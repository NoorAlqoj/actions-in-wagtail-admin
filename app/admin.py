from django.contrib import admin
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
from django.conf import settings
from django.forms import forms
from django.contrib import admin, messages
from django.utils.translation import gettext as _, ngettext
from django.contrib.admin.utils import get_deleted_objects
from django.http.response import (
    HttpResponseBase,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
)
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.safestring import mark_safe
from django.contrib.admin import helpers
from django.db import models
from django.contrib.admin.utils import model_format_dict
from django.http.response import HttpResponseBase
from django.http import HttpResponseRedirect
from django.contrib.admin.views.main import ERROR_FLAG

from .models import Employee


def make_empty(modeladmin, request, queryset):
    queryset.update(lname="")


make_empty.short_description = "Mark selected lastName as empty"


class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["fname", "lname"]
    list_filter = ["fname"]

    actions = [make_empty]


admin.site.register(Employee, EmployeeAdmin)


class IncorrectLookupParameters(Exception):
    pass


@modeladmin_register
class EmployeeAdmin(ModelAdmin):
    model = Employee
    list_display = ["fname", "lname"]
    actions = [make_empty]
  

    list_display = ["action_checkbox", *list_display]
    action_form = helpers.ActionForm
    actions_selection_counter = True
    media = None
    delete_selected_confirmation_template = "modeladmin/delete.html"
    # the methods below is copied from django/contrib/admin/options.py
    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        return helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME, str(obj.pk))

    action_checkbox.short_description = mark_safe(
        '<input type="checkbox" id="action-toggle">'
    )

    def get_action_choices(self, request, default_choices=models.BLANK_CHOICE_DASH):
        """
        Return a list of choices for use in a form object.  Each choice is a
        tuple (name, description).
        """
        choices = [] + default_choices
        for func, name, description in self.get_actions(request).values():
            choice = (name, description % model_format_dict(self.opts))
            choices.append(choice)
        return choices

    def get_action(self, action):
        """
        Return a given action from a parameter, which can either be a callable,
        or the name of a method on the ModelAdmin.  Return is a tuple of
        (callable, name, description).
        """
        # If the action is a callable, just use it.
        if callable(action):
            func = action
            action = action.__name__

        # Next, look for a method. Grab it off self.__class__ to get an unbound
        # method instead of a bound one; this ensures that the calling
        # conventions are the same for functions and methods.
        elif hasattr(self.__class__, action):
            func = getattr(self.__class__, action)

        # Finally, look for a named method on the admin site
        else:
            try:
                func = self.admin_site.get_action(action)
            except KeyError:
                return None

        if hasattr(func, "short_description"):
            description = func.short_description
        else:
            description = capfirst(action.replace("_", " "))
        return func, action, description

    def _get_base_actions(self):
        """Return the list of actions, prior to any request-based filtering."""
        actions = []
        base_actions = (self.get_action(action) for action in self.actions or [])
        # get_action might have returned None, so filter any of those out.
        base_actions = [action for action in base_actions if action]
        base_action_names = {name for _, name, _ in base_actions}

        # Gather actions from the admin site first
        for (name, func) in self.admin_site.actions:
            if name in base_action_names:
                continue
            description = getattr(func, "short_description", name.replace("_", " "))
            actions.append((func, name, description))
        # Add actions from this ModelAdmin.
        actions.extend(base_actions)
        return actions

    def get_actions(self, request):
        """
        Return a dictionary mapping the names of all actions for this
        ModelAdmin to a tuple of (callable, name, description) for each action.
        """
        # If self.actions is set to None that means actions are disabled on
        # this page.
        if self.actions is None or '_popup' in request.GET:

            return {}

        # actions = self._filter_actions_by_permissions(request, self._get_base_actions())
        actions = self._get_base_actions()
        return {name: (func, name, desc) for func, name, desc in actions}

    def get_deleted_objects(self, objs, request):
        """
        Hook for customizing the delete process for the delete view and the
        "delete selected" action.
        """
        return get_deleted_objects(objs, request, self.admin_site)

    def response_action(self, request, queryset):
        """
        Handle an admin action. This is called if a request is POSTed to the
        changelist; it returns an HttpResponse if the action was handled, and
        None otherwise.
        """

        # There can be multiple action forms on the page (at the top
        # and bottom of the change list, for example). Get the action
        # whose button was pushed.
        try:
            action_index = int(request.POST.get("index", 0))
        except ValueError:
            action_index = 0

        # Construct the action form.
        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        # Use the action whose button was pushed
        try:
            data.update({"action": data.getlist("action")[action_index]})
        except IndexError:
            # If we didn't get an action from the chosen form that's invalid
            # POST data, so by deleting action it'll fail the validation check
            # below. So no need to do anything here
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields["action"].choices = self.get_action_choices(request)

        # If the form's valid we can handle the action.
        if action_form.is_valid():
            action = action_form.cleaned_data["action"]
            select_across = action_form.cleaned_data["select_across"]
            func = self.get_actions(request)[action][0]

            # Get the list of selected PKs. If nothing's selected, we can't
            # perform an action on it, so bail. Except we want to perform
            # the action explicitly on all objects.
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

            if not selected and not select_across:
                # Reminder that something needs to be selected or nothing will happen
                msg = _(
                    "Items must be selected in order to perform "
                    "actions on them. No items have been changed."
                )
                messages.warning(request, msg)
                return None

            if not select_across:
                # Perform the action only on the selected objects
                queryset = queryset.filter(pk__in=selected)

            response = func(self, request, queryset)

            # Actions may return an HttpResponse-like object, which will be
            # used as the response from the POST. If not, we'll be a good
            # little HTTP citizen and redirect back to the changelist page.

            if isinstance(response, HttpResponseBase):
                return response
            else:

                return HttpResponseRedirect(request.get_full_path())
        else:
            msg = _("No action selected.")
            messages.success(request, msg)
            # self.message_user(request, msg, messages.WARNING)
            return None
    # changelist_view in options.py 
    def index_view(self, request):
        response = super().index_view(request)
        opts = self.model._meta
        app_label = opts.app_label

        # if not self.has_view_or_change_permission(request):
        #     raise PermissionDenied

        model_name = self.model.__name__.lower()
        if not request.user.has_perms(model_name + ".can_delete_" + model_name):
            messages.error(request, _("No permission."))
            return http.HttpResponse("FAIL, no permission.")
        try:
            cl = self
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given
            # and the 'invalid=1' parameter was already in the query string,
            # something is screwed up with the database, so display an error
            # page.
            if ERROR_FLAG in request.GET:
                # needs to be reviwed
                return SimpleTemplateResponse(
                    "admin/invalid_setup.html", {"title": _("Database error")}
                )
            return HttpResponseRedirect(request.path + "?" + ERROR_FLAG + "=1")

        # If the request was POSTed, this might be a bulk action or a bulk
        # edit. Try to look up an action or confirmation first, but if this
        # isn't an action the POST will fall through to the bulk edit check,
        # below.

        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        actions = self.get_actions(request)

        # Actions with no confirmation
        if (
            actions
            and request.method == "POST"
            and "index" in request.POST
            and "_save" not in request.POST
        ):
            if selected:
                response = self.response_action(
                    request, queryset=cl.get_queryset(request)
                )
                if response:
                    return response
                else:
                    action_failed = True
            else:
                msg = _(
                    "Items must be selected in order to perform "
                    "actions on them. No items have been changed."
                )
                messages.success(request, msg)
                action_failed = True
        # Actions with confirmation
        if (
            actions
            and request.method == "POST"
            and helpers.ACTION_CHECKBOX_NAME in request.POST
            and "index" not in request.POST
            and "_save" not in request.POST
        ):
            if selected:
                response = self.response_action(
                    request, queryset=cl.get_queryset(request)
                )
                if response:
                    return response
                
                else:
                    action_failed = True

        if action_failed:
            # Redirect back to the changelist page to avoid resubmitting the
            # form if the user refreshes the browser or uses the "No, take
            # me back" button on the action confirmation page.
            return HttpResponseRedirect(request.get_full_path())
        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        # formset = cl.formset = None
        
        # needs to be reviewed
        if isinstance(response, HttpResponseNotAllowed):
            # print("HttpResponseNotAllowed")
            response.context_data = {}

        extra = "" if settings.DEBUG else ".min"
        response.context_data["media"] = forms.Media(
            js=[
                "admin/js/vendor/jquery/jquery%s.js" % extra,
                "admin/js/jquery.init.js",
                "admin/js/core.js",
                "admin/js/admin/RelatedObjectLookups.js",
                "admin/js/actions%s.js" % extra,
                "admin/js/urlify.js",
                "admin/js/prepopulate%s.js" % extra,
                "admin/js/vendor/xregexp/xregexp%s.js" % extra,
            ]
        )
        self.media = response.context_data["media"]
        # response.context_data["media"] = forms.Media(js=['admin/js/%s' % url for url in js])

        # Build the action form and populate it with available actions.
        if actions:

            action_form = self.action_form(auto_id=None)
            action_form.fields["action"].choices = self.get_action_choices(request)

            response.context_data["media"] = (
                response.context_data["media"] + action_form.media
            )
            # media += action_form.media
        else:
            action_form = None

        # calculate result_count and result_list

        self.page_num = int(request.GET.get("p", 0))

        paginator = Paginator(self.get_queryset(request), self.list_per_page)
        result_count = paginator.count

        try:
            result_list = paginator.page((self.page_num + 1)).object_list
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            result_list = paginator.page(1).object_list
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            result_list = paginator.page(self.page_num + 1).object_list

        # cl = {"result_count": result_count, "result_list": result_list}
        
        cl = {
            'result_count':result_count,
            'result_list':result_list
        }
        
        selection_note_all = ngettext(
            '%(total_count)s selected',
            'All %(total_count)s selected',
            cl["result_count"]
        )
    
        response.context_data["module_name"] = str(opts.verbose_name_plural)
        response.context_data["selection_note"] = _(
            "0 of %(cnt)s selected" % {"cnt": len(cl["result_list"])},
        )
        response.context_data['selection_note_all'] = _(
            selection_note_all % {'total_count': cl["result_count"]},
        )
        response.context_data["cl"] = cl
        response.context_data["opts"] = opts
        response.context_data["action_form"] = action_form
        response.context_data[
            "actions_selection_counter"
        ] = self.actions_selection_counter
        
        return response
