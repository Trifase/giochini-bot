def test_extract_last_chiavi():
    expected_output = "$config['chiavi'] = 'barbablu, harvard-english-ev, drama-floor-plasti, dance-maze-detect, " \
                      "peace-lunch-empty, stock-mixer-east, total-data-karma';"
    from utils import extract_last_chiavi
    assert extract_last_chiavi(source=test_config_content) == expected_output