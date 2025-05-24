@echo off
echo 🔧 Building standalone executable...
pyinstaller --onefile --windowed id2label.py
echo ✅ Done! Check the dist folder.
pause