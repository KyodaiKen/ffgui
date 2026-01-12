import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class PillBuilder:
    @staticmethod
    def build(flowbox, tags, no_target=False):
        # First, clear existing pills to allow for refreshing
        while child := flowbox.get_first_child():
            flowbox.remove(child)

        if not tags:
            return

        # Handle string or list inputs
        if isinstance(tags, str):
            tags = tags.split(",")
        
        unique_tags = list(dict.fromkeys([t.strip() for t in tags if t.strip()]))

        for tag in unique_tags:
            lbl = Gtk.Label(label=tag)
            lbl.add_css_class("disposition-tag")
            
            # The Magic: If True, the label is invisible to the pointer, 
            # so the click lands on the Button underneath.
            if no_target:
                lbl.set_can_target(False)
                lbl.set_can_focus(False)
                
            flowbox.append(lbl)