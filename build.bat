pyinstaller --noconfirm --clean --log-level=WARN --workpath=_build --specpath=_spec --name=bms-table-view_v1.1.3 main.py
copy README.txt dist\bms-table-view_v1.1.3
copy config.example.json dist\bms-table-view_v1.1.3
