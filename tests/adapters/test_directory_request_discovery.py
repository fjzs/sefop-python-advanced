from adapters.directory_request_discovery import DirectoryRequestDiscovery


def _write_data_json(folder) -> None:
    folder.mkdir(parents=True)
    (folder / "data.json").write_text("{}", encoding="utf-8")


def test__list_ids__given_missing_folder__returns_empty_list(tmp_path):
    # ARRANGE
    discovery = DirectoryRequestDiscovery(folder_path=str(tmp_path / "missing"))

    # ACT / ASSERT
    assert discovery.list_ids() == []


def test__list_ids__returns_only_subfolders_containing_data_json(tmp_path):
    # ARRANGE — "2" and "3" are requests; "notes" has no data.json
    _write_data_json(tmp_path / "2")
    _write_data_json(tmp_path / "3")
    (tmp_path / "notes").mkdir()
    discovery = DirectoryRequestDiscovery(folder_path=str(tmp_path))

    # ACT
    ids = discovery.list_ids()

    # ASSERT
    assert ids == ["2", "3"]


def test__list_ids__returns_ids_sorted_alphabetically(tmp_path):
    # ARRANGE
    _write_data_json(tmp_path / "b")
    _write_data_json(tmp_path / "a")
    discovery = DirectoryRequestDiscovery(folder_path=str(tmp_path))

    # ACT / ASSERT
    assert discovery.list_ids() == ["a", "b"]


def test__list_ids__ignores_files_directly_under_the_folder(tmp_path):
    # ARRANGE
    _write_data_json(tmp_path / "1")
    (tmp_path / "readme.txt").write_text("not a request", encoding="utf-8")
    discovery = DirectoryRequestDiscovery(folder_path=str(tmp_path))

    # ACT / ASSERT
    assert discovery.list_ids() == ["1"]
