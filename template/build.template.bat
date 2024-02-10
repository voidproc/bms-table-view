pyinstaller --noconfirm --clean --log-level=WARN --workpath=_build --specpath=_spec --name=bms-table-view_$version main.py
copy README.txt dist\bms-table-view_$version
copy config.example.json dist\bms-table-view_$version
