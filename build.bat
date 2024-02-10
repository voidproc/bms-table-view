pyinstaller --noconfirm --clean --log-level=WARN --workpath=_build --specpath=_spec --name=bms-table-view_v1.2.0 main.py
copy README.txt dist\bms-table-view_v1.2.0
copy config.example.json dist\bms-table-view_v1.2.0
