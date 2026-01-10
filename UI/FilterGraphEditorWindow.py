import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Graphene, Pango

class FilterGraphEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, filter_data):
        super().__init__(title="Complex Filter Graph Editor", transient_for=parent_window, modal=True)
        self.set_default_size(1000, 700)
        self.app = Gtk.Application.get_default()
        
        # Connection state: stores (source_node, output_idx)
        self.active_connection_source = None 
        self.connections = [] # List of tuples: (src_node, src_out_idx, dest_node, dest_in_idx)

        # Header
        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        btn_apply = Gtk.Button(label="Apply Graph")
        btn_apply.add_css_class("suggested-action")
        header.pack_end(btn_apply)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(main_box)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_start=10, margin_top=10)
        sidebar.set_size_request(180, -1)
        
        lbl_nodes = Gtk.Label(label="<b>Nodes</b>", use_markup=True, xalign=0)
        sidebar.append(lbl_nodes)
        
        btn_add_filter = Gtk.Button(label="Add Filter Node")
        btn_add_filter.connect("clicked", self.on_add_filter_clicked)
        sidebar.append(btn_add_filter)
        
        main_box.append(sidebar)

        # Canvas Setup
        self.canvas = Gtk.Fixed()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.add_css_class("graph-canvas")
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(self.canvas)
        main_box.append(scroll)

    def on_add_filter_clicked(self, _):
        # We use a special "all" type to show every filter in the picker
        from UI.FilterPickerWindow import FilterPickerWindow
        
        def on_selected(filter_obj):
            # Center the new node in the current view
            self.add_node_detailed(filter_obj, 100, 100)

        # Passing None or a specific flag to show all filters
        picker = FilterPickerWindow(self, stream_type="video", on_select=on_selected)
        picker.present()

    def add_node_detailed(self, filter_obj, x, y):
        """Creates a node with proper input/output pins based on FFmpeg metadata."""
        node_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        node_box.add_css_class("graph-node")
        node_box._filter_data = filter_obj
        
        # Header
        header = Gtk.Label(label=f"<b>{filter_obj['name']}</b>", use_markup=True)
        header.add_css_class("node-header")
        node_box.append(header)

        # Body: Contains Pins
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Inputs Column (Left)
        inputs_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        num_inputs = len(filter_obj.get('inputs', [])) or 1 # Default to 1 if not specified
        node_box._input_pins = []
        
        for i in range(num_inputs):
            pin = self._create_pin("input", i, node_box)
            inputs_col.append(pin)
            node_box._input_pins.append(pin)
            
        # Outputs Column (Right)
        outputs_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        num_outputs = len(filter_obj.get('outputs', [])) or 1
        node_box._output_pins = []
        
        for i in range(num_outputs):
            pin = self._create_pin("output", i, node_box)
            outputs_col.append(pin)
            node_box._output_pins.append(pin)

        body.append(inputs_col)
        body.append(Gtk.Box(hexpand=True)) # Middle spacer
        body.append(outputs_col)
        node_box.append(body)

        # Drag Logic
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin", self._on_drag_begin, node_box)
        drag.connect("drag-update", self._on_drag_update, node_box)
        node_box.add_controller(drag)

        self.canvas.put(node_box, x, y)

    def _create_pin(self, pin_type, index, parent_node):
        """Creates an interactive connection point."""
        btn = Gtk.Button()
        btn.add_css_class("graph-pin")
        btn.add_css_class(f"pin-{pin_type}")
        btn.set_tooltip_text(f"{pin_type.capitalize()} {index}")
        
        # Handle connection logic
        btn.connect("clicked", self._on_pin_clicked, pin_type, index, parent_node)
        return btn

    def _on_pin_clicked(self, btn, pin_type, index, node):
        if pin_type == "output":
            # Start a connection
            self.active_connection_source = (node, index)
            btn.add_css_class("pin-active")
        elif pin_type == "input" and self.active_connection_source:
            # Complete a connection
            src_node, src_idx = self.active_connection_source
            self.connections.append((src_node, src_idx, node, index))
            
            print(f"Connected {src_node._filter_data['name']} out:{src_idx} -> {node._filter_data['name']} in:{index}")
            
            # Reset state
            self.active_connection_source = None
            # In a full version, we would call self.queue_draw() to draw the line

    # --- DRAG HANDLERS ---
    def _on_drag_begin(self, gesture, start_x, start_y, node):
        # We need to store where the node started on the canvas
        # Gtk.Fixed doesn't give us current X/Y easily, so we store it
        _, cur_x, cur_y = self.canvas.get_child_position(node)
        node._drag_start_pos = (cur_x, cur_y)

    def _on_drag_update(self, gesture, offset_x, offset_y, node):
        start_x, start_y = node._drag_start_pos
        self.canvas.move(node, start_x + offset_x, start_y + offset_y)