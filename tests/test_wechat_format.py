import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wechat_format as w

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(os.path.dirname(HERE), "example", "article.md")


class Format(unittest.TestCase):
    def test_blocks_and_title(self):
        title, bl = w.blocks(open(EX, encoding="utf-8").read())
        self.assertEqual(title, "示例：用 Markdown 写公众号文章")
        kinds = [b[0] for b in bl]
        for k in ("quote", "p", "h2", "list", "table", "h3"):
            self.assertIn(k, kinds)

    def test_inline_escape_and_bold(self):
        h = w.inline("a <script> & **粗**")
        self.assertIn("&lt;script&gt; &amp;", h); self.assertIn("<strong", h); self.assertNotIn("<script>", h)

    def test_code_span_kept_literal(self):
        h = w.inline("写 `**加粗**` 得到 **加粗**")
        self.assertIn("写 **加粗** 得到 <strong", h); self.assertEqual(h.count("<strong"), 1)

    def test_build_with_figure_and_disclaimer(self):
        out = tempfile.mkdtemp()
        title, n, nf = w.build(EX, out, "摘要", figs=[("比如这一段", "fig1.png", "图 1：示例插图")])
        art = open(os.path.join(out, "article.html"), encoding="utf-8").read()
        self.assertIn("<img src='fig1.png'", art); self.assertIn("图 1：示例插图", art)
        self.assertIn(w.S["small"], art)                       # 文末免责改成灰色小字
        self.assertIn("复制正文（含排版）", open(os.path.join(out, "index.html"), encoding="utf-8").read())

    def test_missing_anchor_fails(self):
        with self.assertRaises(SystemExit):
            w.build(EX, tempfile.mkdtemp(), "摘要", figs=[("不存在的锚点", "x.png", "x")])

    def test_accent(self):
        w.set_accent("#c0392b")
        self.assertIn("#c0392b", w.S["h2"]); self.assertIn("#c0392b", w.S["tip"])
        w.set_accent("#00809f")
        with self.assertRaises(SystemExit):
            w.set_accent("red")


if __name__ == "__main__":
    unittest.main()
