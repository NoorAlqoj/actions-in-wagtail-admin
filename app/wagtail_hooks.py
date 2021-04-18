from django.templatetags.static import static
from django.utils.html import format_html

from wagtail.core import hooks

@hooks.register("insert_global_admin_js", order=100)
def global_admin_js():
 
    return format_html(
        '<script src="{}"></script>',
        static("app/js/prototype.js")
    )