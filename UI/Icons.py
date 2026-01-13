class Icons:
    # Mapping PyAV stream types to GNOME symbolic icons
    TYPE_ICONS = {
        "video": "video-x-generic-symbolic",
        "audio": "audio-x-generic-symbolic",
        "subtitle": "text-x-generic-symbolic",
        "data": "applications-system-symbolic",
        "attachment": "mail-attachment-symbolic",
        "unknown": "image-missing-symbolic"
    }

    # Friendly display names for the UI
    TYPE_DISPLAY_NAMES = {
        "video": "Video",
        "audio": "Audio",
        "subtitle": "Subtitle",
        "data": "Data Stream",
        "attachment": "Attachment",
        "unknown": "Unknown Type"
    }

    @classmethod
    def get_icon_for_type(cls, stream_type):
        """Returns the icon name for a given PyAV stream type."""
        return cls.TYPE_ICONS.get(stream_type.lower(), cls.TYPE_ICONS["unknown"])

    @classmethod
    def get_display_name(cls, stream_type):
        """Returns a capitalized, friendly name for the stream type."""
        return cls.TYPE_DISPLAY_NAMES.get(stream_type.lower(), cls.TYPE_DISPLAY_NAMES["unknown"])

    @classmethod
    def get_all_types(cls):
        """Returns a list of all supported types for DropDowns/Pickers."""
        return ["video", "audio", "subtitle", "data", "attachment"]

    @classmethod
    def is_global_prop(cls, key):
        return key.lower() in cls.GLOBAL_PROPERTIES