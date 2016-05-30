#!/usr/bin/env python

import unittest

from config import Config

class ProxyConfigTest(unittest.TestCase):
    def test_read(self):
        cfg = Config()
        cfg.readCfg("unittest_config_small.xml")
    
        self.assertEqual(cfg.get('port'), "8080")
        self.assertEqual(len(cfg.data['routing']), 2)

    def test_exec(self):
        cfg = Config()
        cfg.readCfg("unittest_config_med.xml")
    
        self.assertEqual(cfg.get('port'), "8080")
        self.assertEqual(len(cfg.data['routing']), 3)
        self.assertEqual(len(cfg.data['exec']), 7)
        
        self.assertEqual(cfg.getEndpoint('/asd'), ['testasd.no', '/pathasd', True])
        
        
        
if __name__ == '__main__':
    unittest.main()