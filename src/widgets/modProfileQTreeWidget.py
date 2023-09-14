
from __future__ import annotations
from typing import TYPE_CHECKING

import PySide6.QtWidgets as qtw
import PySide6.QtGui as qtg
from PySide6.QtCore import Qt as qt, Signal

from widgets.contextMenu import ModContextMenu
from widgets.insertStringQDialog import insertString
from widgets.announcementQDialog import Notice
from widgets.modSelectionQDialog import SelectMod

import errorChecking
from profileManager import ProfileManager
from constant_vars import DATA_PROFILE, DATA_MOD, ROLE_TYPE, ROLE_PARENT, ROLE_INSTALLED

if TYPE_CHECKING:
    from profiles import modProfile

class ProfileList(qtw.QTreeWidget):

    applyProfile = Signal(tuple)

    def __init__(self, parent: modProfile) -> None:
        super().__init__(parent)

        self.setHorizontalScrollBarPolicy(qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.header().setSectionResizeMode(0, qtw.QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, qtw.QHeaderView.ResizeMode.Interactive)

        self.setColumnCount(2)

        self.setHeaderLabels(('Profile', 'Mod Count'))

        self.profileManager = ProfileManager()

        self.menu = ModContextMenu(self)

        self.profileApply = qtg.QAction('Apply Profile')
        self.profileApply.triggered.connect(lambda: self.__applyProfileEvent())

        self.profileAdd = qtg.QAction('Add Profile')
        self.profileAdd.triggered.connect(lambda: self.menuAddProfile())

        self.profileRemove = qtg.QAction('Remove Profile')
        self.profileRemove.triggered.connect(lambda: self.deleteProfile())

        self.profileEdit = qtg.QAction('Change Profile Name')
        self.profileEdit.triggered.connect(lambda: self.editProfileMenu())

        self.profileCopy = qtg.QAction('Copy Profile')
        self.profileCopy.triggered.connect(lambda: self.copyProfile())

        self.modAdd = qtg.QAction('Add Mods')
        self.modAdd.triggered.connect(lambda: self.modAddMenu())

        self.modRemove = qtg.QAction('Remove Mod')
        self.modRemove.triggered.connect(lambda: self.removeMods())

        self.updateView()
    
    def __getProfiles(self) -> list[str]:
        return [x.text(0) for x in self.findItems('*', qt.MatchFlag.MatchWildcard | qt.MatchFlag.MatchWrap | qt.MatchFlag.MatchRecursive)]
    
    def __findProfile(self, profile: str) -> qtw.QTreeWidgetItem:
        return self.findItems(profile, qt.MatchFlag.MatchExactly)[0]
    
    def __getMods(self, profile: qtw.QTreeWidgetItem) -> list[qtw.QTreeWidgetItem] | None:
        '''Returns a list of mod names given the profile'''
        mods: list[str] = []

        for i in range(0, profile.childCount() + 1):

            child = profile.child(i)

            if child is None:
                continue

            mods.append(child)
        
        if not mods:
            return None
        
        return mods
    
    def __applyProfileEvent(self):

        selectedItem = self.__selectedItem()

        if selectedItem is not None:

            if self.isProfile(selectedItem):

                self.applyProfile.emit(tuple(self.profileManager.getMods(selectedItem.text(0))))
            
            else:
                profile = self.__findProfile(selectedItem.data(0, ROLE_PARENT)).text(0)
                self.applyProfile.emit(tuple(self.profileManager.getMods(profile)))
    
    def __selectedItem(self) -> qtw.QTreeWidgetItem | None:
        '''Returns the first object selected in `selectedItems()`'''

        try:

            return self.selectedItems()[0]
        
        except IndexError:

            return None
    
    def checkInstalled(self) -> None:
        '''
        Gives each mod in the tree widget a bool
        depending if it's installed or not.
        '''

        for profile in list(self.profileManager.file.keys()):

            profileWidget = self.__findProfile(profile)

            modsWidget = self.__getMods(profileWidget)

            if not modsWidget:
                continue

            for mod in modsWidget:

                if errorChecking.isInstalled(mod.text(0)):
                    mod.setData(0, ROLE_INSTALLED, True)
                else:
                    mod.setData(0, ROLE_INSTALLED, False)

    def updateView(self) -> None:
        '''Refreshes the whole widget'''
        
        self.clear()

        profile: str
        for profile in list(self.profileManager.file.keys()):

            modList: list[str] = self.profileManager.file.get(profile)

            self.addProfile(profile, initalize=True)

            profileWidget = self.__findProfile(profile)

            profileWidget.setSelected(True)

            # Save is set to false since we know whatever's in the mod list already exists
            self.addMods(*modList, save=False)

            profileWidget.setSelected(False)
            
            self.addTopLevelItem(profileWidget)
        
        self.checkInstalled()
    
    def modAddMenu(self) -> None:
        qDialog = SelectMod()

        qDialog.exec()

        if qDialog.result():

            self.addMods(*qDialog.mods)


    def addMods(self, *mods: str, save: bool = True) -> None:

        selectedItem = self.__selectedItem()

        # If this function was triggered by selecting a mod, find the profile
        if not self.isProfile(selectedItem):
            profile = self.__findProfile(selectedItem.data(0, ROLE_PARENT))
        else:
            profile = selectedItem

        profileMods = self.__getMods(profile)

        if profileMods:
            profileMods = [x.text(0) for x in profileMods]

        for mod in mods:
            
            # Preventing duplicate mods from being added to the GUI
            if profileMods and mod in profileMods:
                continue

            child = qtw.QTreeWidgetItem([mod])
            child.setData(*DATA_MOD)
            child.setData(0, ROLE_PARENT, profile.text(0))
            child.setData(0, ROLE_INSTALLED, True)

            profile.addChild(child)

            profile.setText(1, str(int(profile.text(1)) + 1))
        
        if save:
            self.profileManager.addMod(profile.text(0), *mods)

            if not profile.isExpanded():
                profile.setExpanded(True)
    
    def removeMods(self):

        mod = self.__selectedItem()

        profile = self.__findProfile(mod.data(0, ROLE_PARENT))

        self.profileManager.removeMod(profile.text(0), mod.text(0))

        profile.takeChild(profile.indexOfChild(mod))

        profile.setText(1, str(int(profile.text(1)) - 1))
    
    def menuAddProfile(self):
        '''
        Prompts the user to ask what the profile
        should be before running `addProfile()`

        If the user tries to input a duplicate profile name
        raise an error and try it again
        '''

        qDialog = insertString('Profile name:')

        while True:
            
            qDialog.exec()

            if not qDialog.result():
                break

            elif qDialog.userInput:

                if qDialog.userInput not in self.__getProfiles():
                    self.addProfile(qDialog.userInput)
                    break
                else:
                    msg = Notice('A profile with this name already exists.', 
                                 'Error: Duplicate profile name')
                    msg.exec()

    def addProfile(self, *items: str, initalize: bool = False) -> None:
        '''
        Adds one or more new profiles to the list
        
        The initalize parameter is when the program loads from the json file
        '''

        profiles = self.__getProfiles()

        for item in items:

            if item in profiles:
                continue

            profile = qtw.QTreeWidgetItem([item, '0'])
            profile.setData(*DATA_PROFILE)
            self.addTopLevelItem(profile)
        
        if not initalize:
            self.profileManager.addProfile(*items)
    
    def isProfile(self, itemInQuestion: qtw.QTreeWidgetItem) -> bool:
        return itemInQuestion.data(0, ROLE_TYPE) == DATA_PROFILE[2]

    def deleteProfile(self):
        '''Deletes an existing profile'''

        toBeDeleted = self.__selectedItem()

        self.takeTopLevelItem(self.indexOfTopLevelItem(toBeDeleted))

        self.profileManager.removeProfile(toBeDeleted.text(0))
    
    def editProfileMenu(self):

        qDialog = insertString('New profile name:')

        while True:
            
            qDialog.exec()

            if not qDialog.result():
                break

            elif qDialog.userInput:

                if qDialog.userInput not in self.__getProfiles():
                    self.editProfile(qDialog.userInput)
                    break
                else:
                    msg = Notice('A profile with this name already exists.', 
                                 'Error: Duplicate profile name')
                    msg.exec()

    def editProfile(self, name: str):
        '''Changes the name of a profile'''

        profile = self.__selectedItem()

        self.profileManager.changeProfile(profile.text(0), name)

        profile.setText(0, name)
    
    def copyProfile(self):

        profileToCopy = self.__selectedItem()

        modsToCopy = [x.text(0) for x in self.__getMods(profileToCopy)]

        qDialog = insertString('New profile name:')

        while True:

            qDialog.exec()

            if not qDialog.result():
                break

            elif qDialog.userInput:

                if qDialog.userInput not in self.__getProfiles():

                    self.addProfile(qDialog.userInput)

                    profileItem = self.__findProfile(qDialog.userInput)

                    profileItem.setSelected(True)

                    profileToCopy.setSelected(False)

                    self.addMods(*modsToCopy)

                    break
                else:
                    msg = Notice('A profile with this name already exists.', 
                                 'Error: Duplicate profile name')
                    msg.exec()

    def unselectShortcut(self):
        toBeUnselected = self.__selectedItem()
        if toBeUnselected:
            toBeUnselected.setSelected(False)



# EVENT OVERRIDES
    def mousePressEvent(self, event: qtg.QMouseEvent) -> None:

        if event.button() == qt.MouseButton.RightButton:

            selectedItems = self.selectedItems()

            if selectedItems:

                for item in selectedItems:
                    if self.isProfile(item):
                        self.menu.addActions((self.profileApply, self.modAdd, self.profileRemove, self.profileEdit, self.profileCopy))
                    else:
                        self.menu.addActions((self.profileApply, self.modAdd, self.modRemove))
            
            else:
                self.menu.addAction(self.profileAdd)
            
            self.menu.exec(qtg.QCursor.pos())

            self.menu.clear()

        elif event.button() == qt.MouseButton.LeftButton:

            if not self.itemAt(qtg.QCursor.pos()):
                self.clearSelection()

        return super().mousePressEvent(event)
    
    def keyPressEvent(self, event: qtg.QKeyEvent) -> None:

        selectedItem = self.__selectedItem()

        if selectedItem is None:
            return

        if event.key() == qt.Key.Key_Delete or event.key() == qt.Key.Key_Backspace:

            if not self.isProfile(selectedItem):

                self.removeMods()
        
        elif event.key() == qt.Key.Key_Return:

            if self.isProfile(selectedItem):

                self.editProfileMenu()

        return super().keyPressEvent(event)
