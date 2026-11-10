"""Isolated tests using dummy ComfyUI modules, no actual ComfyUI needed."""
import asyncio
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

class DummyRoutes:
    def get(self, path):
        return lambda fn: fn
    def post(self, path):
        return lambda fn: fn

class TestCameraPromptPresets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        fake_folder = types.ModuleType("folder_paths")
        fake_folder.get_input_directory = lambda: cls.temporary.name
        fake_server = types.ModuleType("server")
        fake_server.PromptServer = type('PromptServer', (), {'instance':types.SimpleNamespace(routes=DummyRoutes())})
        sys.modules['folder_paths'] = fake_folder
        sys.modules['server'] = fake_server
        spec=importlib.util.spec_from_file_location('camera_prompt_test_nodes', PROJECT / 'nodes.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_all_included(self):
        presets=self.module._load_presets('built_in:early_mobile_phone.json')
        self.assertEqual(len(presets), 34)
        self.assertEqual(len({p['title'] for p in presets}), 34)
        self.assertTrue(all(p['prompt'] for p in presets))

    def test_append_and_outputs(self):
        node=self.module.CameraPromptPresets()
        result=node.compose('A young dog running outdoors.', 'built_in:early_mobile_phone.json', 'Quick | Medium')
        self.assertTrue(result[0].startswith('A young dog running outdoors.\n\n'))
        self.assertEqual(result[1], next(p['prompt'] for p in self.module._load_presets('built_in:early_mobile_phone.json') if p['title'] == 'Quick | Medium'))
        self.assertEqual(result[2], 'Quick | Medium')

    def test_empty_base(self):
        node=self.module.CameraPromptPresets()
        final, suffix, _=node.compose('', 'built_in:early_mobile_phone.json', 'Quick | Mild')
        self.assertEqual(final, suffix)

    def test_validate_dynamic_selection(self):
        node=self.module.CameraPromptPresets
        self.assertIs(node.VALIDATE_INPUTS('built_in:early_mobile_phone.json','Quick | Medium'), True)
        self.assertIsInstance(node.VALIDATE_INPUTS('built_in:early_mobile_phone.json','Does not exist'), str)

    def test_invalid_json(self):
        for bad in (b'{', b'[]', b'{"presets":[]}', b'{"presets":[{"title":"x"}]}'):
            with self.assertRaises(ValueError): self.module._read_and_validate(bad)

    def test_duplicate_names(self):
        payload={'presets':[{'title':'Foo','prompt':'One'},{'title':'foo','prompt':'Two'}]}
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.module._read_and_validate(json.dumps(payload).encode())

    def test_no_path_traversal(self):
        with self.assertRaises(ValueError):
            self.module._resolve_library('uploaded:../../passwd.json')

    def test_hash_changes_with_uploaded_file(self):
        folder=self.module.UPLOAD_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        path=folder / 'test.json'
        path.write_text(json.dumps({'presets':[{'title':'One','prompt':'X'}]}),'utf-8')
        node=self.module.CameraPromptPresets
        old=node.IS_CHANGED('base','uploaded:test.json','One')
        path.write_text(json.dumps({'presets':[{'title':'One','prompt':'Y'}]}),'utf-8')
        new=node.IS_CHANGED('base','uploaded:test.json','One')
        self.assertNotEqual(old,new)

    def test_list_endpoint(self):
        class R:
            query={'library':'built_in:early_mobile_phone.json'}
        response=asyncio.run(self.module.list_presets(R()))
        self.assertEqual(response.status,200)
        self.assertEqual(len(json.loads(response.body)['presets']),34)

if __name__ == '__main__': unittest.main()
