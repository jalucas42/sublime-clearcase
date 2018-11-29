import os
import sublime
import sublime_plugin
import subprocess
import time
import re


class ProcessHelper:
    _cmd    = [];
    _stdout = "";
    _stderr = "";
    _retval = None;

    def execute(self, cmd):
        # if windows
        if (sublime.platform() == "windows"):
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, shell=False, creationflags=subprocess.SW_HIDE)
        else:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    

        output, stderr = p.communicate()

        self._cmd    = cmd;
        self._stdout = output.decode()
        self._stderr = stderr.decode()
        self._retval = p.returncode

    def execute_bg(self, cmd):
        # if windows
        if (sublime.platform() == "windows"):
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, shell=False, creationflags=subprocess.SW_HIDE)
        else:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    

        #output, stderr = p.communicate()

        self._cmd    = cmd;
        self._stdout = None; #output.decode()
        self._stderr = None; #stderr.decode()
        self._retval = None; #p.returncode

    def get_stdout(self):
        return self._stdout

    def get_stderr(self):
        return self._stderr

    def get_retval(self):
        return self._retval

    def get_cmd(self):
        return self._cmd

    def get_cmd_as_string(self):
        # FIXME: Wrap the individual args in quotes so that command can be copy-pasted.
        return " ".join(self._cmd)


class ClearcaseHelper:
    ph = ProcessHelper()

    def __init__(self):
        None

    def print_debug(self,filepath):
        print("ClearcaseHelper debug info for " + filepath)
        print("get_current_comment:         " + str(self.get_current_comment(filepath)))
        print("is_checkedout:         " + str(self.is_checkedout(filepath)))
        print("is_checkedin:         " + str(self.is_checkedin(filepath)))
        print("is_private:         " + str(self.is_private(filepath)))

    def get_current_comment(self, filepath):
        
        cmd = [
            'cleartool',
            'describe',
            '-fmt',
            '%Nc',
            filepath,
        ];

        ph = ProcessHelper()
        ph.execute(cmd)
        return ph.get_stdout()


    def is_checkedout(self, filepath):

        cmd = [
            'cleartool',
            'describe',
            '-fmt',
            '%Vn',
            filepath,
        ];

        ph = ProcessHelper()
        ph.execute(cmd)

        version_id = ph.get_stdout()

        if re.search(r"/CHECKEDOUT$", version_id):
            return True
        else:
            return False


    def is_checkedin(self, filepath):
        cmd = [
            'cleartool',
            'describe',
            '-fmt',
            '%Vn',
            filepath,
        ];

        ph = ProcessHelper()
        ph.execute(cmd)

        version_id = ph.get_stdout()
        if re.search(r"/CHECKEDOUT$", version_id):
            return False
        
        elif len(version_id) == 0:
            return False
        else:
            return True

    def is_private(self, filepath):
        cmd = [
            'cleartool',
            'describe',
            '-fmt',
            '%Vn',
            filepath,
        ];

        ph = ProcessHelper()
        ph.execute(cmd)

        version_id = ph.get_stdout()

        if len(version_id) == 0:
            return True
        else:
            return False

    def get_pred_filename(self, filepath):
        ph = ProcessHelper()

        cmd = [
            'cleartool',
            'describe',
            '-fmt',
            '%En@@%PVn',
            filepath,
        ];

        ph.execute(cmd)
        return ph.get_stdout()


class ClearcaseCommand(sublime_plugin.WindowCommand):
    _comment = "";
    _cmd     = [];
    cc       = ClearcaseHelper();
    ph       = ProcessHelper()

    def run(self):
        None

    def run_cmd(self, cmd):
        if len(self.window.active_view().file_name()) > 0:

            ph = ProcessHelper()

            ph.execute(cmd)

            # Create a 'find_in_files' output panel, or fetch the existing one.
            win   = sublime.active_window()
            panel = win.create_output_panel("clearcase_output_panel")
            win.run_command('show_panel',{"panel":"output.clearcase_output_panel"})
            
            # Make the panel writeable.  If it already existed from a previous search, it would be read-only.
            panel.set_read_only(False);
            print("Running: " + " ".join(cmd) + "\n\n");
            panel.run_command("append", {"characters": "Running: " + ph.get_cmd_as_string() + "\n\n"})
            panel.run_command("append", {"characters": ph.get_stdout()})
            panel.run_command("append", {"characters": ph.get_stderr()})
            panel.set_read_only(True);


    def is_enabled(self):
        return self.window.active_view().file_name() and len(self.window.active_view().file_name()) > 0


class ClearcaseCheckoutCommand(ClearcaseCommand):
    reserved_switch = '-reserved'

    def run(self):
        self.step1();
        #print("Comment is: " + self.comment);
        #cmd = ['cleardlg', '/checkout', self.window.active_view().file_name()]
        #super(ClearcaseCheckoutCommand, self).run(cmd)

    def step1(self):        
        self.window.show_input_panel('Comment: ', '', self.step2, None, None)

    def step2(self, val):

        self._comment = val;

        self._cmd = [
            'cleartool', 
            'co',
            self.reserved_switch,
            '-c',
            self._comment,
            self.window.active_view().file_name(),
        ];

        print("Running: " + " ".join(self._cmd));

        super(ClearcaseCheckoutCommand, self).run_cmd(self._cmd)

    def is_enabled(self):
        if not super(ClearcaseCheckoutCommand, self).is_enabled():
            return False

        return self.cc.is_checkedin(self.window.active_view().file_name())


class ClearcaseCheckoutUnreservedCommand(ClearcaseCheckoutCommand):
    
    reserved_switch = '-unreserved'




class ClearcaseCheckinCommand(ClearcaseCommand):
    def run(self):
        self.step1();

    def step1(self):        
        exiting_comment = self.cc.get_current_comment(self.window.active_view().file_name())
        self.window.show_input_panel('Comment: ', existing_comment, self.step2, None, None)

    def step2(self, val):

        self._comment = val;

        self._cmd = [
            'cleartool', 
            'ci',
            '-c',
            self._comment,
            self.window.active_view().file_name(),
        ];

        self.run_cmd(self._cmd)

    def is_enabled(self):
        if not super().is_enabled():
            return False

        return self.cc.is_checkedout(self.window.active_view().file_name())

# JAL: Version tree command doesn't work - need to debug!
class ClearcaseVtreeCommand(ClearcaseCommand):
    def run(self):
        
        # JAL: For some reason, the version tree tool does not launch currently.
        # It pops open a gui status window which flashes some messages and closes.
        # The version tree should pop up after the status window closes - this is 
        # what it does from the terminal.  Instead, the status window closes and 
        # nothing else happens.  Bummer.
        cmd = [
            'cleartool',
            'lsvtree',
            '-graphical',
            self.window.active_view().file_name(),
        ]

        self.ph.execute_bg(cmd)


    def is_enabled(self):     
        if not super().is_enabled():
            return False

        return not self.cc.is_private(self.window.active_view().file_name())


class ClearcasePrevCommand(ClearcaseCommand):
    def run(self):
        
        cmd = [
            'kdiff3',
            self.window.active_view().file_name(),
            self.cc.get_pred_filename(self.window.active_view().file_name()),
        ]

        self.ph.execute_bg(cmd)

    def is_enabled(self):
        if not super().is_enabled():
            return False

        return not self.cc.is_private(self.window.active_view().file_name())


class ClearcaseUncoCommand(ClearcaseCommand):
    def run(self):
        dialog_message = ''.join([
            'You are about to undo checkout of:\n',
            '\n',
            self.window.active_view().file_name()+"\n",
            "\n",
            "Do you want to save a .keep file?\n",
        ])
        retval = sublime.yes_no_cancel_dialog(dialog_message)

        if retval == sublime.DIALOG_CANCEL:
            return

        if retval == sublime.DIALOG_YES:
            keep_switch = "-keep"

        keep_switch = "-keep" if (retval == sublime.DIALOG_YES) else "-rm"

        self._cmd = [
            'cleartool', 
            'unco',
            keep_switch,
            self.window.active_view().file_name(),
        ];

        self.run_cmd(self._cmd)


    def is_enabled(self):
        if not super().is_enabled():
            return False

        return self.cc.is_checkedout(self.window.active_view().file_name())


class ClearcaseNewcinCommand(ClearcaseCommand):
    def run(self):
        dialog_message = ''.join([
            'Do you really want to add this file to Clearcase?\n',
            '\n',
            self.window.active_view().file_name()+"\n",
        ])
        retval = sublime.yes_no_cancel_dialog(dialog_message)


        if retval == sublime.DIALOG_YES:
            self._cmd = [
                'cleartool', 
                'mkelem',
                '-mkpath',
                '-nc',
                '-nco',
                self.window.active_view().file_name(),
            ];

            self.run_cmd(self._cmd)


    def is_enabled(self):
        if not super().is_enabled():
            return False

        return self.cc.is_private(self.window.active_view().file_name())


