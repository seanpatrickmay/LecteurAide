from app.services.segmentation import split_into_scenes, split_into_sentences


def test_split_into_scenes():
    text = "Scene 1.\n\nScene 2."
    scenes = split_into_scenes(text)
    assert scenes == ["Scene 1.", "Scene 2."]


def test_split_into_sentences():
    scene = "Hello world. Goodbye."
    sentences = split_into_sentences("english", scene)
    assert len(sentences) >= 2
