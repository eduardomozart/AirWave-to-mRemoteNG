from export_to_mremoteng import parse_folders

def test_parse_folders_valid(sample_folder_xml):
    folders, fl = parse_folders(sample_folder_xml)
    assert fl is not None
    assert len(fl) == 7
    # "Top" should be omitted from the folders dictionary
    assert "1" not in folders
    assert len(folders) == 6

    # Verify Campus A
    assert "10" in folders
    assert folders["10"]["name"] == "Campus A"
    assert folders["10"]["parent_id"] == "1"
    assert folders["10"]["folder_path"] == "Top > Campus A"
    assert folders["10"]["subfolders"] == []
    assert folders["10"]["devices"] == []

    # Verify Building 1 under Campus A
    assert "101" in folders
    assert folders["101"]["name"] == "Building 1"
    assert folders["101"]["parent_id"] == "10"
    assert folders["101"]["folder_path"] == "Top > Campus A > Building 1"

    # Verify Building 1 under Campus B
    assert "201" in folders
    assert folders["201"]["name"] == "Building 1"
    assert folders["201"]["parent_id"] == "20"
    assert folders["201"]["folder_path"] == "Top > Campus B > Building 1"

def test_parse_folders_empty_or_malformed():
    folders, fl = parse_folders("")
    assert folders == {}
    assert fl is None

    folders, fl = parse_folders("<invalid><xml>")
    assert folders == {}
    assert fl is None

def test_parse_folders_no_top():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <amp:amp_folder_list xmlns:amp="http://www.airwave.com">
      <folder id="10">
        <name>Root Campus</name>
        <parent_id>0</parent_id>
      </folder>
    </amp:amp_folder_list>
    """
    folders, fl = parse_folders(xml)
    assert "10" in folders
    assert folders["10"]["name"] == "Root Campus"
    assert folders["10"]["folder_path"] == "Root Campus"

def test_parse_folders_with_folderlist_instance(sample_folder_xml):
    from airwaveapiclient import FolderList
    fl_obj = FolderList(sample_folder_xml)
    folders, fl = parse_folders(fl_obj)
    assert fl is fl_obj
    assert len(folders) == 6
    assert "10" in folders
    assert fl.search(10) is not None
    assert fl.search(10)['name'] == 'Campus A'
