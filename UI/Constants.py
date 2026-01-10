MENU_XML = """
    <?xml version='1.0' encoding='UTF-8'?>
    <interface>
        <menu id='app-menu'>
            <section>
                <item>
                    <attribute name='label'>Open Job List</attribute>
                    <attribute name='action'>win.open_joblist</attribute>
                </item>
                <item>
                    <attribute name='label'>Save Job List</attribute>
                    <attribute name='action'>win.save_joblist</attribute>
                </item>
                <item>
                    <attribute name='label'>Clear Job List</attribute>
                    <attribute name='action'>win.clear_joblist</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>New job</attribute>
                    <attribute name='action'>win.create_job</attribute>
                </item>
                <item>
                    <attribute name='label'>Create jobs from a directory of files</attribute>
                    <attribute name='action'>win.create_jobs_from_dir</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>Preferences</attribute>
                    <attribute name='action'>win.pref</attribute>
                </item>
                <item>
                    <attribute name='label'>Template Manager</attribute>
                    <attribute name='action'>win.tplm</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>About</attribute>
                    <attribute name='action'>win.about</attribute>
                </item>
                <item>
                    <attribute name='label'>Quit</attribute>
                    <attribute name='action'>win.quit</attribute>
                </item>
            </section>
        </menu>
    </interface>
    """

CONTEXT_MENU_XML = """
<?xml version='1.0' encoding='UTF-8'?>
<interface>
  <menu id='context-menu'>
    <section>
        <item>
            <attribute name='label'>Edit Job...</attribute>
            <attribute name='action'>context.job_setup</attribute>
        </item>
        <item>
            <attribute name='label'>Clone Job...</attribute>
            <attribute name='action'>context.job_clone</attribute>
        </item>
        <item>
            <attribute name='label'>Remove Job</attribute>
            <attribute name='action'>context.remove_job</attribute>
        </item>
    </section>
    <section>
        <attribute name='label'>Useful Tools</attribute>
        <submenu>
            <attribute name='label'>Stream Toggle</attribute>
            <item>
                <attribute name='label'>Toggle All Video Streams</attribute>
                <attribute name='action'>context.toggle_video</attribute>
            </item>
            <item>
                <attribute name='label'>Toggle All Audio Streams</attribute>
                <attribute name='action'>context.toggle_audio</attribute>
            </item>
            <item>
                <attribute name='label'>Toggle All Subtitle Streams</attribute>
                <attribute name='action'>context.toggle_subtitles</attribute>
            </item>
        </submenu>
        <submenu>
            <attribute name='label'>Batch Apply Template</attribute>
            <item>
                <attribute name='label'>Video Streams...</attribute>
                <attribute name='action'>context.batch_tpl_video</attribute>
            </item>
            <item>
                <attribute name='label'>Audio Streams...</attribute>
                <attribute name='action'>context.batch_tpl_audio</attribute>
            </item>
            <item>
                <attribute name='label'>Subtitle Streams...</attribute>
                <attribute name='action'>context.batch_tpl_subtitle</attribute>
            </item>
        </submenu>
    </section>
  </menu>
</interface>
"""