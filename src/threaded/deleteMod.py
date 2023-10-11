import logging
import os
import shutil

from threaded.file_mover import FileMover
from constant_vars import OPTIONS_DISPATH, MODS_DISABLED_PATH_DEFAULT

class DeleteMod(FileMover):
    def __init__(self, *mods: str):
        super().__init__()

        self.mods = mods
    
    def run(self) -> None:
        self.deleteMod(*self.mods)
        return super().run()
    
    def deleteMod(self, *mods: str) -> None:
        '''Removes the mod(s) from the user's computer'''

        self.setTotalProgress.emit(len(mods))

        disPath = self.optionsManager.getOption(OPTIONS_DISPATH, fallback=MODS_DISABLED_PATH_DEFAULT)

        try: 
            for modName in mods:

                if self.cancel: raise Exception('cancel')

                self.setCurrentProgress.emit(1, f'Deleting {modName}')

                enabled = self.saveManager.isEnabled(modName)

                type = self.saveManager.getType(modName) if enabled else 'disabled'

                self.saveManager.removeMods(modName)

                path = self.p.mod(type, modName) if type != 'disabled' else disPath

                if os.path.exists(path):
                    shutil.rmtree(path, onerror=self.onError)
                else:
                    logging.error('An error was raised in FileMover.deleteMod(), mod path does not exist:\n%s', path)

            self.succeeded.emit()

        except Exception as e:

            if str(e) == 'cancel':
                logging.info('Canceled deleteMod()')

            else:
                logging.error('An error has occured in deleteMod():\n%s', str(e))
                self.error.emit(str(e))