using Gtk;
using Gio;


var application = Gtk.Application.New("com.kyo.ffgui", ApplicationFlags.FlagsNone);

application.OnActivate += (sender, args) =>
{
    // 1. Create Window
    var window = ApplicationWindow.New((Gtk.Application)sender);
    window.Title = "GTK4 .NET 8 List Manager";
    window.SetDefaultSize(400, 600);

    // 2. Setup Layout
    var mainBox = Box.New(Orientation.Vertical, 10);
    mainBox.SetMarginTop(12);
    mainBox.SetMarginBottom(12);
    mainBox.SetMarginStart(12);
    mainBox.SetMarginEnd(12);

    // 3. Search Bar
    var searchEntry = SearchEntry.New();
    mainBox.Append(searchEntry);

    // 4. List View (Simple String List)
    var listBox = ListBox.New();
    listBox.SetSelectionMode(SelectionMode.Single);
    
    // ScrolledWindow makes the list scrollable
    var scrolledWindow = ScrolledWindow.New();
    scrolledWindow.SetChild(listBox);
    scrolledWindow.SetVexpand(true); // Fill remaining space
    mainBox.Append(scrolledWindow);

    // 5. Add Button
    var addButton = Button.NewWithLabel("Add Item");
    addButton.OnClicked += (s, e) => {
        var row = Label.New($"New Item {DateTime.Now:T}");
        listBox.Append(row);
    };
    mainBox.Append(addButton);

    window.SetChild(mainBox);
    window.Present();
};

return application.Run(args);