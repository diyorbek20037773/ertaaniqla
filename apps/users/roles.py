"""CMS roles and the moderation workflow (spec §1.1, M7).

Three Wagtail groups:

* **Editor** (copywriter) — creates and edits pages in both languages, submits translations and
  pages for moderation, manages media, videos, glossary terms, institutions and FAQ questions.
  Cannot publish.
* **Medical Reviewer** (doctor) — reviews pages submitted to the "Medical review" workflow (the
  task gives editor access to the page under review), answers FAQ questions, edits glossary
  definitions. Approval publishes the page with the "Verified by a doctor" badge.
* **Admin** (content lead / developer) — everything editors can do plus publish, delete, site
  settings, redirects, CMS users, workflows and feedback submissions.

`ensure_roles()` is idempotent: it only adds what is missing and never removes permissions an
admin granted by hand. It runs after every `migrate` (post_migrate) and via `manage.py setup_roles`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.apps import apps as global_apps
from django.contrib.auth.models import Group, Permission
from django.db import transaction

logger = logging.getLogger(__name__)

EDITOR = "Editor"
MEDICAL_REVIEWER = "Medical Reviewer"
ADMIN = "Admin"
ROLE_NAMES = (EDITOR, MEDICAL_REVIEWER, ADMIN)

WORKFLOW_NAME = "Medical review"
TASK_NAME = "Medical review (doctor)"
WAGTAIL_DEFAULT_GROUPS = ("Editors", "Moderators")
WAGTAIL_DEFAULT_WORKFLOW = "Moderators approval"

IMAGE = "media_library.portalimage"
DOCUMENT = "media_library.portaldocument"


@dataclass(frozen=True)
class Role:
    name: str
    # "app_label.codename" model/global permissions
    permissions: tuple[str, ...] = ()
    # page permission codenames granted on the tree root (covers every locale tree)
    page_permissions: tuple[str, ...] = ()
    # "app_label.model" → codenames for image/document collection permissions on the root collection
    collection_permissions: dict[str, tuple[str, ...]] = field(default_factory=dict)


def _crud(model: str, *actions: str) -> tuple[str, ...]:
    app_label, model_name = model.split(".")
    return tuple(f"{app_label}.{action}_{model_name}" for action in actions)


ADMIN_ACCESS = ("wagtailadmin.access_admin",)
TRANSLATE = ("wagtail_localize.submit_translation",)

ROLES: tuple[Role, ...] = (
    Role(
        name=EDITOR,
        permissions=(
            *ADMIN_ACCESS,
            *TRANSLATE,
            *_crud("media_library.video", "add", "change", "view"),
            *_crud("glossary.term", "add", "change", "view"),
            *_crud("directory.institution", "add", "change", "view"),
            *_crud("directory.region", "view"),
            *_crud("directory.service", "view"),
            *_crud("faq.question", "change", "view"),
        ),
        page_permissions=("add_page", "change_page", "lock_page"),
        collection_permissions={
            IMAGE: ("add", "change", "choose"),
            DOCUMENT: ("add", "change", "choose"),
        },
    ),
    Role(
        name=MEDICAL_REVIEWER,
        permissions=(
            *ADMIN_ACCESS,
            *_crud("media_library.video", "view"),
            *_crud("glossary.term", "change", "view"),
            *_crud("directory.institution", "view"),
            *_crud("faq.question", "change", "view"),
        ),
        collection_permissions={IMAGE: ("choose",), DOCUMENT: ("choose",)},
    ),
    Role(
        name=ADMIN,
        permissions=(
            *ADMIN_ACCESS,
            *TRANSLATE,
            *_crud("media_library.video", "add", "change", "delete", "view"),
            *_crud("glossary.term", "add", "change", "delete", "view"),
            *_crud("directory.institution", "add", "change", "delete", "view"),
            *_crud("directory.region", "add", "change", "view"),
            *_crud("directory.service", "add", "change", "view"),
            *_crud("faq.question", "add", "change", "delete", "view"),
            *_crud("feedback.feedbacksubmission", "change", "delete", "view"),
            *_crud("core.sitesettings", "change"),
            *_crud("wagtailredirects.redirect", "add", "change", "delete"),
            *_crud("users.user", "add", "change", "delete"),
            *_crud("wagtailcore.workflow", "add", "change", "delete"),
            *_crud("wagtailcore.task", "add", "change", "delete"),
            *_crud("wagtailcore.site", "change"),
            *_crud("wagtailcore.locale", "add", "change"),
        ),
        page_permissions=(
            "add_page",
            "change_page",
            "lock_page",
            "publish_page",
            "bulk_delete_page",
            "unlock_page",
        ),
        collection_permissions={
            IMAGE: ("add", "change", "choose", "delete"),
            DOCUMENT: ("add", "change", "choose", "delete"),
        },
    ),
)


def _permission(dotted: str) -> Permission:
    app_label, codename = dotted.split(".", 1)
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


def _model_permission(model: str, action: str) -> Permission:
    app_label, model_name = model.split(".")
    return Permission.objects.get(
        content_type__app_label=app_label, codename=f"{action}_{model_name}"
    )


def ensure_permissions_exist(using: str = "default") -> None:
    """post_migrate fires per app; make sure every app's content types and permissions exist."""
    from django.contrib.auth.management import create_permissions
    from django.contrib.contenttypes.management import create_contenttypes

    for app_config in global_apps.get_app_configs():
        create_contenttypes(app_config, verbosity=0, using=using)
        create_permissions(app_config, verbosity=0, using=using)


@transaction.atomic
def ensure_roles() -> dict[str, Group]:
    from wagtail.models import (
        Collection,
        GroupCollectionPermission,
        GroupPagePermission,
        Page,
    )

    root_page = Page.get_first_root_node()
    root_collection = Collection.get_first_root_node()
    groups: dict[str, Group] = {}
    for role in ROLES:
        group, created = Group.objects.get_or_create(name=role.name)
        if created:
            logger.info("created CMS group %s", role.name)
        group.permissions.add(*(_permission(p) for p in role.permissions))
        if root_page is not None:
            for codename in role.page_permissions:
                GroupPagePermission.objects.get_or_create(
                    group=group,
                    page=root_page,
                    permission=Permission.objects.get(
                        content_type__app_label="wagtailcore", codename=codename
                    ),
                )
        if root_collection is not None:
            for model, actions in role.collection_permissions.items():
                for action in actions:
                    GroupCollectionPermission.objects.get_or_create(
                        group=group,
                        collection=root_collection,
                        permission=_model_permission(model, action),
                    )
        groups[role.name] = group
    ensure_workflow(groups[MEDICAL_REVIEWER])
    _remove_unused_wagtail_default_groups()
    return groups


def ensure_workflow(reviewers: Group) -> Any:
    """Create the "Medical review" workflow with one `MedicalReviewTask`, assigned to the tree root.

    Assigning it to the root page (depth 1) covers the uz and ru trees and every future locale.
    Wagtail's default "Moderators approval" workflow is replaced on the root; a workflow an admin
    assigned by hand is left alone.
    """
    from wagtail.models import Page, Workflow, WorkflowPage, WorkflowTask

    from apps.users.models import MedicalReviewTask

    task = MedicalReviewTask.objects.filter(name=TASK_NAME).first()
    if task is None:
        task = MedicalReviewTask.objects.create(name=TASK_NAME)
    task.groups.add(reviewers)

    workflow, _created = Workflow.objects.get_or_create(name=WORKFLOW_NAME)
    if not WorkflowTask.objects.filter(workflow=workflow, task=task).exists():
        WorkflowTask.objects.create(workflow=workflow, task=task, sort_order=0)

    root_page = Page.get_first_root_node()
    if root_page is None:
        return workflow
    assignment = WorkflowPage.objects.filter(page=root_page).select_related("workflow").first()
    if assignment is None:
        WorkflowPage.objects.create(page=root_page, workflow=workflow)
    elif assignment.workflow.name == WAGTAIL_DEFAULT_WORKFLOW:
        default = assignment.workflow
        assignment.workflow = workflow
        assignment.save(update_fields=["workflow"])
        if (
            not default.workflow_pages.exists()
            and not default.workflow_states.filter(status="in_progress").exists()
        ):
            default.active = False
            default.save(update_fields=["active"])
    return workflow


def _remove_unused_wagtail_default_groups() -> None:
    """Wagtail's initial migration creates "Editors" and "Moderators"; they would be confused
    with our roles. Delete them while nobody is a member."""
    for group in Group.objects.filter(name__in=WAGTAIL_DEFAULT_GROUPS):
        if not group.user_set.exists():
            group.delete()
