#!/bin/sh

rm -r ../NMRBrew/dist/
#python setup.installers.py bdist_mac --qt-menu-nib=/usr/local/Cellar/qt5/5.2.1/plugins/platforms/
python setup.mac.py py2app

# https://bitbucket.org/ronaldoussoren/py2app/issue/26/bundled-python-executable-not-working
cp /Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python ./dist/NMRBrew.app/Contents/MacOS/python
install_name_tool -change /Library/Frameworks/Python.framework/Versions/2.7/Python @executable_path/../Frameworks/Python.framework/Versions/2.7/Python dist/NMRBrew.app/Contents/MacOS/python

#https://github.com/andreyvit/yoursway-create-dmg
create-dmg \
--volname "NMRBrew" \
--volicon "./nmrbrew/static/icon.icns" \
--window-pos 200 120 \
--window-size 800 400 \
--icon-size 100 \
--icon NMRBrew.app 200 190 \
--hide-extension NMRBrew.app \
--app-drop-link 600 185 \
NMRBrew.dmg \
./dist/ 

mv NMRBrew.dmg ./dist/NMRBrew.dmg
#--background "installer_background.png" \
