"""CMS roles, permissions and the medical review workflow (M7)."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import Client
from django.utils import timezone
from wagtail.models import GroupApprovalTask, Locale, Page, Workflow, WorkflowPage, WorkflowTask

from apps.articles.models import ArticlePage
from apps.users.models import MedicalReviewTask
from apps.users.roles import (
    ADMIN,
    EDITOR,
    MEDICAL_REVIEWER,
    ROLE_NAMES,
    WAGTAIL_DEFAULT_GROUPS,
    WORKFLOW_NAME,
    ensure_roles,
)

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-battery-staple"


def make_user(username: str, role: str, **extra: Any) -> Any:
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.uz", password=PASSWORD, **extra
    )
    user.groups.add(Group.objects.get(name=role))
    return user


@pytest.fixture
def editor(db):
    return make_user("copywriter", EDITOR)


@pytest.fixture
def reviewer(db):
    return make_user(
        "doctor", MEDICAL_REVIEWER, first_name="Dilfuza", last_name="A.", organisation="RONC"
    )


@pytest.fixture
def content_admin(db):
    return make_user("contentlead", ADMIN)


@pytest.fixture
def article(seeded) -> ArticlePage:
    return ArticlePage.objects.get(slug="belgilar", locale__language_code="uz")


# --- roles ------------------------------------------------------------------------------------


def group_permission_counts() -> dict[str, int]:
    return {g.name: g.permissions.count() for g in Group.objects.filter(name__in=ROLE_NAMES)}


def test_roles_created_by_migrate_and_idempotent() -> None:
    assert set(group_permission_counts()) == set(ROLE_NAMES)
    assert not Group.objects.filter(name__in=WAGTAIL_DEFAULT_GROUPS).exists()
    before = group_permission_counts()
    ensure_roles()
    out = StringIO()
    call_command("setup_roles", stdout=out)
    assert "roles and workflow are up to date" in out.getvalue()
    assert group_permission_counts() == before
    assert Workflow.objects.filter(name=WORKFLOW_NAME).count() == 1
    assert MedicalReviewTask.objects.count() == 1


def test_workflow_assigned_to_root_covers_both_locales(article) -> None:
    root = Page.get_first_root_node()
    assert WorkflowPage.objects.get(page=root).workflow.name == WORKFLOW_NAME
    ru = ArticlePage.objects.get(
        translation_key=article.translation_key, locale__language_code="ru"
    )
    assert article.get_workflow().name == WORKFLOW_NAME
    assert ru.get_workflow().name == WORKFLOW_NAME


def test_manually_granted_permissions_are_kept() -> None:
    editor_group = Group.objects.get(name=EDITOR)
    extra = Permission.objects.get(codename="view_feedbacksubmission")
    editor_group.permissions.add(extra)
    ensure_roles()
    assert editor_group.permissions.filter(pk=extra.pk).exists()


def test_hand_assigned_root_workflow_is_left_alone(article) -> None:
    root = Page.get_first_root_node()
    custom = Workflow.objects.create(name="Custom")
    WorkflowPage.objects.filter(page=root).update(workflow=custom)
    ensure_roles()
    assert WorkflowPage.objects.get(page=root).workflow == custom


def test_editor_permissions(editor, article) -> None:
    perms = article.permissions_for_user(editor)
    assert perms.can_edit()
    assert perms.can_add_subpage()
    assert not perms.can_publish()
    assert not perms.can_unpublish()
    assert editor.has_perm("wagtailadmin.access_admin")
    assert editor.has_perm("wagtail_localize.submit_translation")
    assert editor.has_perm("glossary.change_term")
    assert not editor.has_perm("glossary.delete_term")
    assert not editor.has_perm("feedback.view_feedbacksubmission")  # PII: admins only
    assert not editor.has_perm("core.change_sitesettings")
    assert not editor.has_perm("users.add_user")


def test_reviewer_permissions(reviewer, article) -> None:
    perms = article.permissions_for_user(reviewer)
    assert not perms.can_edit()
    assert not perms.can_publish()
    assert reviewer.has_perm("wagtailadmin.access_admin")
    assert reviewer.has_perm("faq.change_question")  # doctors answer questions
    assert reviewer.has_perm("glossary.change_term")
    assert not reviewer.has_perm("glossary.add_term")
    assert not reviewer.has_perm("feedback.view_feedbacksubmission")


def test_admin_permissions(content_admin, article) -> None:
    perms = article.permissions_for_user(content_admin)
    assert perms.can_edit() and perms.can_publish() and perms.can_unpublish()
    for perm in (
        "core.change_sitesettings",
        "wagtailredirects.add_redirect",
        "users.change_user",
        "feedback.view_feedbacksubmission",
        "wagtailcore.change_workflow",
    ):
        assert content_admin.has_perm(perm), perm
    assert not content_admin.is_superuser


@pytest.mark.parametrize(
    ("role", "edit_ok", "users_ok"),
    [("editor", True, False), ("reviewer", False, False), ("content_admin", True, True)],
)
def test_cms_access_per_role(request, article, role: str, edit_ok: bool, users_ok: bool) -> None:
    user = request.getfixturevalue(role)
    client = Client()
    client.force_login(user)
    assert client.get("/cms/").status_code == 200
    edit = client.get(f"/cms/pages/{article.pk}/edit/")
    assert (edit.status_code == 200) is edit_ok, edit.status_code
    users = client.get("/cms/users/")
    assert (users.status_code == 200) is users_ok, users.status_code


def test_review_fields_not_in_page_form(editor, article) -> None:
    client = Client()
    client.force_login(editor)
    html = client.get(f"/cms/pages/{article.pk}/edit/").content.decode()
    assert 'name="medically_verified"' not in html
    assert 'name="last_reviewed_by"' not in html
    assert "Not medically verified yet." in html


# --- workflow -----------------------------------------------------------------------------------


def submit(page: Any, user: Any) -> Any:
    page.title = page.title + " (tahrir)"
    page.save_revision(user=user)
    return page.get_workflow().start(page, user)


def test_editor_submits_reviewer_approves_publishes_with_badge(editor, reviewer, article) -> None:
    workflow_state = submit(article, editor)
    task_state = workflow_state.current_task_state
    task = task_state.task.specific
    assert isinstance(task, MedicalReviewTask)
    assert task.get_actions(article, editor) == []
    assert task.user_can_access_editor(article, reviewer)
    assert not task.user_can_access_editor(article, editor)
    assert [a[0] for a in task.get_actions(article, reviewer)] == ["reject", "approve", "approve"]
    assert task.get_task_states_user_can_moderate(reviewer).count() == 1
    assert task.get_task_states_user_can_moderate(editor).count() == 0

    task.on_action(task_state, reviewer, "approve")

    article = ArticlePage.objects.get(pk=article.pk)
    workflow_state.refresh_from_db()
    assert workflow_state.status == "approved"
    assert article.live and not article.has_unpublished_changes
    assert article.title.endswith("(tahrir)")
    assert article.medically_verified is True
    assert article.last_reviewed_by == reviewer
    assert article.last_reviewed_at == timezone.localdate()
    assert article.verified_badge["organisation"] == "RONC"
    # the badge survives later edits (the form never touches the fields)
    article.save_revision(user=editor)
    assert article.get_latest_revision_as_object().medically_verified is True


def test_reviewer_edits_during_review_through_cms(editor, reviewer, article) -> None:
    submit(article, editor)
    client = Client()
    client.force_login(reviewer)
    assert client.get(f"/cms/pages/{article.pk}/edit/").status_code == 200
    dashboard = client.get("/cms/").content.decode()
    assert "(tahrir)" in dashboard  # "awaiting your review" panel


def test_rejection_does_not_publish_or_verify(editor, reviewer, article) -> None:
    workflow_state = submit(article, editor)
    task_state = workflow_state.current_task_state
    task_state.task.specific.on_action(task_state, reviewer, "reject", comment="manba kerak")
    article = ArticlePage.objects.get(pk=article.pk)
    assert article.has_unpublished_changes
    assert not article.medically_verified
    assert not article.title.endswith("(tahrir)")


def test_superuser_outside_reviewer_group_cannot_approve(admin_user, editor, article) -> None:
    workflow_state = submit(article, editor)
    task = workflow_state.current_task_state.task.specific
    assert task.get_actions(article, admin_user) == []
    assert not task.locked_for_user(article, admin_user)
    assert task.get_task_states_user_can_moderate(admin_user).count() == 0


def test_workflow_without_medical_task_publishes_unverified(editor, article) -> None:
    plain = Workflow.objects.create(name="Plain")
    step = GroupApprovalTask.objects.create(name="Plain step")
    step.groups.add(Group.objects.get(name=ADMIN))
    WorkflowTask.objects.create(workflow=plain, task=step, sort_order=0)
    WorkflowPage.objects.filter(page=Page.get_first_root_node()).update(workflow=plain)
    lead = make_user("lead2", ADMIN)
    workflow_state = submit(article, editor)
    task_state = workflow_state.current_task_state
    task_state.task.specific.on_action(task_state, lead, "approve")
    article = ArticlePage.objects.get(pk=article.pk)
    assert article.title.endswith("(tahrir)")
    assert not article.medically_verified


def test_copies_and_translations_start_unreviewed(reviewer, article) -> None:
    article.medically_verified = True
    article.last_reviewed_by = reviewer
    article.last_reviewed_at = timezone.localdate()
    article.save_revision().publish()
    copy = article.copy(update_attrs={"slug": "belgilar-nusxa", "title": "nusxa"})
    assert not copy.medically_verified and copy.last_reviewed_by is None
    en = Locale.objects.create(language_code="en")
    translated = article.copy_for_translation(en, copy_parents=True)
    assert not translated.medically_verified
    assert translated.last_reviewed_by is None
