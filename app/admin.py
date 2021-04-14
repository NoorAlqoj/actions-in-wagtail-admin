from django.contrib import admin
from wagtail.contrib.modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register,
)
 
from .models import Employee

def make_empty(modeladmin, request, queryset):
    queryset.update(lname='')

make_empty.short_description =('Mark selected lastName as empty')    

class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["fname","lname"]
    actions = [make_empty]
    
admin.site.register(Employee,EmployeeAdmin)   
 
from django.utils.safestring import mark_safe
from django.contrib.admin import helpers
from django.db import models
from django.contrib.admin.utils import model_format_dict

class IncorrectLookupParameters(Exception):
    pass

@modeladmin_register
class EmployeeAdmin(ModelAdmin):
    model = Employee
    list_display = ["fname","lname"]
    actions = [make_empty]
    
    action_form = helpers.ActionForm
    actions_selection_counter = True
    
    # the methods below is copied from django/contrib/admin/options.py
    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        return helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME, str(obj.pk))
    action_checkbox.short_description = mark_safe('<input type="checkbox" id="action-toggle">')

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

        if hasattr(func, 'short_description'):
            description = func.short_description
        else:
            description = capfirst(action.replace('_', ' '))
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
            description = getattr(func, 'short_description', name.replace('_', ' '))
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
        if self.actions is None :# or IS_POPUP_VAR in request.GET:
    
            return {}

        # actions = self._filter_actions_by_permissions(request, self._get_base_actions())
        actions = self._get_base_actions()
        return {name: (func, name, desc) for func, name, desc in actions}

    def index_view(self, request):
        response = super().index_view(request)
        from django.contrib.admin.views.main import ERROR_FLAG
        opts = self.model._meta
        app_label = opts.app_label

     
        if self.get_actions(request):
            if not 'action_checkbox' in self.list_display:
                self.list_display = ['action_checkbox', *self.list_display]
       
        
      
        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        actions = self.get_actions(request)
        
       
        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_queryset(request))
                if response:
                    return response
                else:
                    action_failed = True
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg, messages.WARNING)
                action_failed = True
        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_queryset(request))
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


        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
            # media += action_form.media
        else:
            action_form = None
        # selection_note_all = ngettext(
        #     '%(total_count)s selected',
        #     'All %(total_count)s selected',
        #     cl.result_count
        # )
        # context = {
        #     **self.admin_site.each_context(request),
        #     'module_name': str(opts.verbose_name_plural),
        #     # 'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
        #     # 'selection_note_all': selection_note_all % {'total_count': cl.result_count},
        #     'title': cl.title,
        #     'is_popup': cl.is_popup,
        #     'to_field': cl.to_field,
        #     # 'cl': cl,
        #     'media': media,
        #     'has_add_permission': self.has_add_permission(request),
        #     'opts': cl.opts,
        #     'action_form': action_form,
        #     'actions_on_top': self.actions_on_top,
        #     'actions_on_bottom': self.actions_on_bottom,
        #     'actions_selection_counter': self.actions_selection_counter,
        #     'preserved_filters': self.get_preserved_filters(request),
        #     **(extra_context or {}),
        # }        
        
        ## review  
        # response.context_data = context  
        
        response.context_data['opts'] = opts
        response.context_data['action_form'] = action_form 
        response.context_data['actions_selection_counter'] = self.actions_selection_counter
        return response
        