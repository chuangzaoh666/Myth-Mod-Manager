import shutil
import os

from PySide6.QtCore import QThread, Signal, QUrl

from save import Save, OptionsManager
from widgets.announcementQDialog import Notice
from getPath import Pathing
import errorChecking
from constant_vars import MOD_TYPE, TYPE_MODS, OPTIONS_DISPATH, MODS_DISABLED_PATH_DEFAULT, TYPE_MODS_OVERRIDE, BACKUP_MODS, MODSIGNORE, TYPE_MAPS


class FileMover(QThread):
    '''
    File Manager of the program.

    Any function that involves moving files goes here.

    !IMPORTANT!
    
    Should usually not be ran by itself, please use `progress()` from `widgets.progressWidget`
    or something similar

    This allows it to properly thread and use the class' signals for the `QProgressBar`

    The mode parameter is to choose which function you want (Since it needs to be
    wrapped in `run()`)

    Possible parameters:
    
    + 0 : moveToDisabledDir(*mods: str)
    + 1 : moveToEnableModDir(*mods: str)
    + 2 : changeModType(*mods: str | QUrl)
    + 3 : unZipMod(tuple[str, str])
    + 4 : deleteMod(modName: str)
    + 5 : backupMods()
    '''

    setTotalProgress = Signal(int)

    setCurrentProgress = Signal(int, str)

    succeeded = Signal()

    error = Signal(str)

    cancel = False

    def __init__(self, mode: int, *args):
        super().__init__()

        self.mode = mode

        self.args = args

        self.saveManager = Save()
        self.optionsManager = OptionsManager()

        self.p = Pathing()

        self.modeDict = {0 : lambda: self.moveToDisabledDir(*args),
                         1 : lambda: self.moveToEnableModDir(*args),
                         2 : lambda: self.changeModType(*args),
                         3 : lambda: self.unZipMod(*args),
                         4 : lambda: self.deleteMod(*args),
                         5 : self.backupMods}
    
    def run(self) -> None:

        self.modeDict[self.mode]()

        return super().run()

    def moveToDisabledDir(self, *mods: str) -> None:
        '''Moves a mod to the disabled folder'''

        self.setTotalProgress.emit(len(mods))

        disabledModsPath = self.optionsManager.getOption(OPTIONS_DISPATH, fallback=MODS_DISABLED_PATH_DEFAULT)

        errorChecking.createDisabledModFolder()

        for mod in mods:

            if self.cancel: break

            self.setCurrentProgress.emit(1, f'Disabling {mod}')

            # Checking if the mod is already in the disabled mods folder
            if not mod in os.listdir(disabledModsPath):

                modPath = self.p.mod(self.saveManager.getType(mod), mod)

                shutil.move(modPath, disabledModsPath)
        
        self.succeeded.emit()

    def moveToEnableModDir(self, *mods: str) -> None:
        '''Returns a mod to their respective directory'''

        self.setTotalProgress.emit(len(mods))

        disabledModsPath = self.optionsManager.getOption(OPTIONS_DISPATH, fallback=MODS_DISABLED_PATH_DEFAULT)

        errorChecking.createDisabledModFolder()

        for mod in mods:

            if self.cancel: break

            self.setCurrentProgress.emit(1, f'Enabling {mod}')

            if mod in os.listdir(disabledModsPath):

                modDestPath = self.p.mod(self.saveManager.getType(mod), mod)

                shutil.move(os.path.join(disabledModsPath, mod), modDestPath)
        
        self.succeeded.emit()
    
    def changeModType(self, *mods: tuple[QUrl, str]) -> None:
        '''
        Moves the mod to a new directory

        The 1st index of the tuple should be a constant var
        '''

        self.setTotalProgress.emit(len(mods))

        ChosenDir = None
        
        for mod in mods:
            
            # If the current set of args are URLs to folders
            if type(mod) == tuple:

                modURL = mod[0]
                ChosenDir = mod[1]
                
                modsDirPath = modURL.toLocalFile()

                mod = modURL.fileName()

            self.setCurrentProgress.emit(1, f'Installing {mod}')

            # Setting the Destination path
            if errorChecking.isTypeMod(ChosenDir):

                modDestPath = self.p.mod(ChosenDir, mod)

                if not os.path.exists(modDestPath):
                    shutil.move(modsDirPath, modDestPath)
        
        self.succeeded.emit()

    def unZipMod(self, *mods: tuple[QUrl, str]) -> None:
        '''Asks the user where each mod will go and then unzips it to that directory'''

        self.setTotalProgress.emit(len(mods))

        try:

            for modURL in mods:

                url = modURL[0]

                src = url.toLocalFile()

                mod = url.fileName()

                type = modURL[1]

                modDestDict = {TYPE_MODS : self.p.mods(), TYPE_MODS_OVERRIDE : self.p.mod_overrides(), TYPE_MAPS : self.p.maps()}

                if self.cancel: break

                self.setCurrentProgress.emit(1, f"Unpacking {mod}")

                if os.path.exists(src):

                        if src.endswith('.rar'):

                            self.rarNotSupported.emit(mod)

                            continue

                        shutil.unpack_archive(src, modDestDict[type])

        except Exception as e:

            self.error.emit(str(e))
        
        self.succeeded.emit()
    
    def deleteMod(self, *mods: str) -> None:
        '''Removes the mod(s) from the user's computer'''

        self.setTotalProgress.emit(len(mods))

        disPath = self.optionsManager.getOption(OPTIONS_DISPATH, fallback=MODS_DISABLED_PATH_DEFAULT)

        for modName in mods:

            if self.cancel: break

            self.setCurrentProgress.emit(1, f'Deleting {modName}')

            enabled = self.saveManager.isEnabled(modName)

            type = self.saveManager.getType(modName) if enabled else 'disabled'

            self.saveManager.removeMods(modName)

            path = self.p.mod(type, modName) if type != 'disabled' else disPath

            if os.path.exists(path):
                shutil.rmtree(path)

        self.succeeded.emit()

    def backupMods(self) -> None:
        '''Takes all of the mods and compresses them into a zip file, the output is in the exe directory'''

        # Step 1: Gather Options

        disPath = self.optionsManager.getOption(OPTIONS_DISPATH, fallback=MODS_DISABLED_PATH_DEFAULT)

        # Step 2: Set Paths

        modPath = self.p.mods()

        mod_overridePath = self.p.mod_overrides()

        maps_path = self.p.maps()

        bundledFilePath = os.path.join(os.path.abspath(os.curdir), BACKUP_MODS)

        bundledModsPath = os.path.join(bundledFilePath, 'mods')
        
        bundledOverridePath = os.path.join(bundledFilePath, 'assets', 'mod_overrides')

        bundledMapsPath = os.path.join(bundledFilePath, 'Maps')

        outputPathDict = {TYPE_MODS_OVERRIDE : bundledOverridePath, TYPE_MODS : bundledModsPath, TYPE_MAPS : bundledMapsPath}

        srcPathDict = {TYPE_MODS_OVERRIDE : mod_overridePath, TYPE_MODS : modPath, TYPE_MAPS : maps_path}

        try:
            
            # Step 4: Create Folders

            # Every mod
            mods = list([x for x in os.listdir(modPath) if x not in MODSIGNORE] + os.listdir(mod_overridePath) + os.listdir(disPath) + os.listdir(maps_path))

            self.setTotalProgress.emit(len(mods) + 3) # Add 3 for the extra steps that aren't the list lengeth

            self.setCurrentProgress.emit(1, f'Validating backup folder paths')
            # Backup folder
            if not os.path.exists(bundledFilePath):

                os.mkdir(bundledFilePath)

            # /mods
            if not os.path.exists(bundledModsPath):

                os.mkdir(bundledModsPath)

            # /assets/mod_overrides
            if not os.path.exists(bundledOverridePath):

                os.makedirs(bundledOverridePath)

            # /Maps
            if not os.path.exists(bundledMapsPath):
                os.mkdir(bundledMapsPath)

            # Step 5: Copy each mod into the backup folder
            for mod in (x for x in mods):

                if self.cancel: raise Exception('Task was canceled')

                self.setCurrentProgress.emit(1, f'Copying {mod} to {BACKUP_MODS}')

                modType = self.saveManager.get(mod, MOD_TYPE)

                # If the mod is disabled then the src will go to the disabled mods directory
                src = os.path.join(srcPathDict[modType], mod) if self.saveManager.isEnabled(mod) else os.path.join(disPath, mod)

                output = os.path.join(outputPathDict[modType], mod)

                # shutil.copytree() can't overwrite files, so if it already exists it must be deleted first
                if os.path.exists(output):

                    shutil.rmtree(output)

                shutil.copytree(src, output)
            
            # Step 6: Zip Backup folder
            self.setCurrentProgress.emit(1, f'Zipping to {bundledFilePath}')

            # Create Zip, this should overwrite if it already exists
            shutil.make_archive(BACKUP_MODS, 'zip', bundledFilePath)

            # Step 7: Cleanup

            self.setCurrentProgress.emit(1, 'Cleanup')
            # Delete Folder
            shutil.rmtree(bundledFilePath)

            self.succeeded.emit()
            
        except Exception as e:

            # If something goes wrong, delete the unfinished bundled file
            if os.path.exists(bundledFilePath):
                shutil.rmtree(bundledFilePath)

            if not self.cancel:
                self.error.emit(str(e))
