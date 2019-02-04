import os
import sublime
import sublime_plugin
import subprocess
import time
import re
import random
import pprint

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
    ph    = ProcessHelper()
    debug = False
    pp    = pprint.PrettyPrinter(indent=4)
    cache = {}

    def __init__(self):
        print("in ClearcaseHelper.__init__()")
        None

    def print_debug(self,filepath):
        self.flush_cache()
        self.pp.pprint(self.get_info(filepath))

    def flush_cache(self):
        self.cache = {}

    def get_info(self, filepath):

        curtime = time.time()

        # Check if we have cached info for the requested file, and if the 
        # cached data is outdated yet.  Return the cached info if possible.
        if (filepath in self.cache and curtime-self.cache[filepath]["time"] < 10):
            self.debug and print("Using cached info for " + filepath)
        
        # No cached data is available.  Analyze the file and cache the results.
        else:
            self.debug and print("Fetching fresh info for " + filepath)

            # Run clearcase "describe" on the requested file.
            fldsep = str(random.random())
            fmt = fldsep.join(["%n", "%Vn", "%Nc", "%PVn", "%Vd", "%Fu", "%e", "%En@@%PVn", "%Rf"])
            cmd = [
                'cleartool',
                'describe',
                '-fmt',
                fmt,
                filepath,
            ];

            self.ph.execute(cmd)

            # Split the results into fields
            fields = self.ph.get_stdout().split(fldsep)
            self.debug and self.pp.pprint(fields)

            # Populate our 'element' object.  This contains all the useful info
            # for the requested file.
            element                    = {}
            element["filepath"]        = filepath
            element["time"]            = curtime
            element["version_id"]      = fields[1]
            element["comment"]         = fields[2]
            element["is_private"]      = (fields[0] == "<name-unknown>")
            element["is_reserved"]     = (fields[8] == "reserved")
            element["is_unreserved"]   = (fields[8] == "unreserved")
            element["is_checkedout"]   = element["is_reserved"] or element["is_unreserved"]
            element["pred_version_id"] = fields[3]
            element["pred_filepath"]   = fields[7]
            element["user"]            = fields[5]
            element["is_dir"]          = os.path.isdir(filepath)
            element["is_in_view"]      = True if re.match('^/view/', filepath) else False;

            # Cache the info
            self.cache[filepath] = element

        # Always return data from the cache.  
        self.debug and self.pp.pprint(self.cache[filepath])
        return self.cache[filepath]


    def get_current_comment(self, filepath):       
        return self.get_info(filepath)["comment"]

    def is_checkedout(self, filepath):
        return self.get_info(filepath)["is_checkedout"]

    def is_checkedin(self, filepath):
        return not(self.get_info(filepath)["is_private"]) and not(self.get_info(filepath)["is_checkedout"])

    def is_private(self, filepath):
        return self.get_info(filepath)["is_private"]

    def get_pred_filename(self, filepath):
        return self.get_info(filepath)["pred_filepath"]

    def is_dir(self, filepath):
        return self.get_info(filepath)["is_dir"]

    def is_in_view(self, filepath):
        return self.get_info(filepath)["is_in_view"]




class ClearcaseCommand(sublime_plugin.WindowCommand):
    _cmd           = [];
    cc             = ClearcaseHelper();
    ph             = ProcessHelper()
    args           = {};
    filepaths      = [];
    pp             = pprint.PrettyPrinter(indent=4)
    debug          = False
    cleartool_path = "cleartool"

    def run(self):
        None

    def print_debug(self, str):
        if self.debug:
            print(str)

    def get_files(self):

        # Update the settings
        # This seems like an odd thing to do in GET_FILES, but it gets called
        # by every method, so is quite handy.
        # FIXME: settings don't seem to be loading for some reason
        #self.debug          = self.window.active_view().settings().get('clearcase.debug'          , False)
        #self.cleartool_path = self.window.active_view().settings().get('clearcase.cleartool_path' , False)

        if self.debug:
            print("Running get_files with arg:")
            self.pp.pprint(self.args)
        
        if self.args and "paths" in self.args and len(self.args["paths"]):
            self.filepaths = self.args["paths"]
        elif len(self.window.active_view().file_name()) > 0:
            self.filepaths = [ self.window.active_view().file_name() ]
        else:
            self.filepaths = []

        if self.debug:
            print("Set self.filepaths to:")
            self.pp.pprint(self.filepaths)


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
            self.debug and print("Running: " + " ".join(cmd) + "\n\n");
            panel.run_command("append", {"characters": "Running: " + ph.get_cmd_as_string() + "\n\n"})
            panel.run_command("append", {"characters": ph.get_stdout()})
            panel.run_command("append", {"characters": ph.get_stderr()})
            panel.set_read_only(True);


    def is_enabled(self):

        # Make sure all files are under /view/...
        for filepath in self.filepaths:
            if not self.cc.is_in_view(filepath):
                self.print_debug(self.cc.get_info(filepath))
                return False

        # There needs to be at least one file available
        if ( len(self.filepaths) < 1 ):
            return False

        return True
            

class ClearcaseCheckoutCommand(ClearcaseCommand):
    reserved_switch = '-reserved'

    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return 

        self.step1();

    def step1(self):
        if (len(self.filepaths) == 1):     
            self.window.show_input_panel('Enter a checkout comment (1 file): ', '', self.step2, None, None)
        else:
            self.window.show_input_panel('Enter a checkout comment ('+str(len(self.filepaths))+' files): ', '', self.step2, None, None)

    def step2(self, val):

        comment = val;

        self._cmd = [
            'cleartool', 
            'co',
            self.reserved_switch,
            '-c',
            comment,
        ];
        self._cmd.extend(self.filepaths)

        super(ClearcaseCheckoutCommand, self).run_cmd(self._cmd)


    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if self.cc.is_private(filepath) or self.cc.is_checkedout(filepath):
                return False

        return True



class ClearcaseCheckoutUnreservedCommand(ClearcaseCheckoutCommand):
    
    reserved_switch = '-unreserved'




class ClearcaseCheckinCommand(ClearcaseCommand):

    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return 

        self.step1();

    def step1(self):        
        existing_comment = self.cc.get_current_comment(self.filepaths[0])
        self.window.show_input_panel('Comment: ', existing_comment, self.step2, None, None)

        if (len(self.filepaths) == 1):     
            self.window.show_input_panel('Enter a checkin comment (1 file): ', existing_comment, self.step2, None, None)
        else:
            self.window.show_input_panel('Enter a checkin comment ('+str(len(self.filepaths))+' files): ', existing_comment, self.step2, None, None)


    def step2(self, val):

        self._comment = val;

        self._cmd = [
            'cleartool', 
            'ci',
            '-c',
            self._comment,
        ];
        self._cmd.extend(self.filepaths)

        self.run_cmd(self._cmd)


    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if not(self.cc.is_checkedout(filepath)):
                return False

        return True


## JAL: Version tree GUI command doesn't work - need to debug!
#class ClearcaseVtreeCommand(ClearcaseCommand):
#    def run(self):
#
#        # JAL: For some reason, the version tree tool does not launch currently.
#        # It pops open a gui status window which flashes some messages and closes.
#        # The version tree should pop up after the status window closes - this is 
#        # what it does from the terminal.  Instead, the status window closes and 
#        # nothing else happens.  Bummer.
#        self._cmd = [
#           'xclearcase',
#           '-display',
#           ':2',
#           '-vtree',
#           self.window.active_view().file_name(),
#        ]
#
#        self._cmd = [
#            'cleartool',
#            'lsvtree',
#            '-graphical',
#            self.window.active_view().file_name(),
#        ];
#
#        print(" ".join(self._cmd))
#        self.ph.execute(self._cmd)
#
#        print(self.ph._stderr)
#        print(self.ph._stdout)
#
#        print("finished launching vtree") 
#
#
#    def is_enabled(self):
#        return True;     
#        if not super().is_enabled():
#            return False
#
#        return not self.cc.is_private(self.window.active_view().file_name())
#
#
### JAL: Version tree command doesn't work - need to debug!
##class ClearcaseVtreeCommand(ClearcaseCommand):
##    def run(self):
##        
##        # JAL: For some reason, the version tree tool does not launch currently.
##        # It pops open a gui status window which flashes some messages and closes.
##        # The version tree should pop up after the status window closes - this is 
##        # what it does from the terminal.  Instead, the status window closes and 
##        # nothing else happens.  Bummer.
##        self._cmd = [
##            'cleartool',
##            'lsvtree',
##            '-all',
##            self.window.active_view().file_name(),
##        ]
##
##        self.run_cmd(self._cmd)
##
##
##    def is_enabled(self):     
##        if not super().is_enabled():
##            return False
##
##        return not self.cc.is_private(self.window.active_view().file_name())


class ClearcasePrevCommand(ClearcaseCommand):
    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return
        
        for filepath in self.filepaths:
            cmd = [
                'kdiff3',
                filepath,
                self.cc.get_pred_filename(filepath),
            ]

            self.ph.execute_bg(cmd)

    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if self.cc.is_private(filepath):
                return False

        return True


class ClearcaseUncoCommand(ClearcaseCommand):
    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return

        dialog_message = ''.join([
            'You are about to undo checkout of:\n',
            '\n',
            "\n".join(self.filepaths)+"\n",
            "\n",
            "Do you want to save a .keep file?\n",
        ])
        retval = sublime.yes_no_cancel_dialog(dialog_message)

        if retval == sublime.DIALOG_CANCEL:
            return

        if retval == sublime.DIALOG_YES:
            keep_switch = "-keep"
        else: 
            keep_switch = "-rm"

        # keep_switch = (retval == sublime.DIALOG_YES) ? "-keep" : "-rm"

        self._cmd = [
            'cleartool', 
            'unco',
            keep_switch,
        ];
        self._cmd.extend(self.filepaths)

        self.run_cmd(self._cmd)


    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return false

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if not(self.cc.is_checkedout(filepath)):
                return False

        return True


class ClearcaseNewcinCommand(ClearcaseCommand):
    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return

        if self.debug:
            print("checkout requested for these files")
            self.pp.pprint(self.filepaths)

        dialog_message = ''.join([
            'xxxDo you really want to add these files to Clearcase?\n',
            '\n',
            '\n'.join(self.filepaths)+"\n",
        ])
        retval = sublime.yes_no_cancel_dialog(dialog_message)


        if retval == sublime.DIALOG_YES:
            self._cmd = [
                'cleartool', 
                'mkelem',
                '-mkpath',
                '-nc',
                '-nco',
            ];
            self._cmd.extend(self.filepaths)

            self.run_cmd(self._cmd)


    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if not(self.cc.is_private(filepath)):
                return False

        return True


class ClearcaseFindCheckoutsCommand(ClearcaseCommand):
    def run(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        cmd = [
            '/home/a0866383/bin/find_checkouts',
        ]
        cmd.extend(self.filepaths)

        # FIXME: find_checkouts is coming up blank for some reason.
        self.pp.pprint(cmd)
        
        self.ph.execute_bg(cmd)

    def is_enabled(self, **args):
        self.args = args
        self.get_files()
        if not(self.filepaths):
            return False

        if not super().is_enabled():
            return False

        for filepath in self.filepaths:
            if not(re.match('^/view/', filepath)):
                return False
            if not(self.cc.is_dir(filepath)):
                return False

        return True
