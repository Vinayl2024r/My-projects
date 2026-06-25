## 发布 LinkedIn 帖子 workflow

1. 打开 LinkedIn 发帖页面：`agent-browser --auto-connect open "https://www.linkedin.com/feed/"`
2. 查看交互元素：`agent-browser --auto-connect snapshot -i`
3. 点击 `发帖` 入口按钮（通常显示为"开始帖子"/"Start a post"）：`agent-browser --auto-connect click @发帖按钮`
4. 等待弹窗出现：`agent-browser --auto-connect wait 1000`
5. 查看交互元素：`agent-browser --auto-connect snapshot -i`
6. 输入帖子内容：`agent-browser --auto-connect fill @内容输入框 "{帖子内容}"`
7. （可选）上传图片/视频：
   - 点击媒体上传按钮（相机/照片图标）：`agent-browser --auto-connect click @媒体按钮`
   - 查看元素：`agent-browser --auto-connect snapshot -i`
   - 上传文件：`agent-browser --auto-connect upload @文件上传输入框 "{文件路径}"`
   - 等待上传完成：`agent-browser --auto-connect wait 3000`
8. （可选）添加话题标签：在内容中直接输入 `#话题`
9. 查看当前状态：`agent-browser --auto-connect snapshot -i`
10. 停留在编辑页，提示用户手动确认发布，不自动点击"发布"按钮

## 元素参考（示例，实际以 snapshot 为准）

| 元素 | 功能 | 说明 |
|------|------|------|
| `button "开始帖子"` / `button "Start a post"` | 发帖入口 | 首页发帖触发按钮 |
| `textbox` / `div[contenteditable]` | 内容输入框 | 帖子正文编辑区 |
| `button "照片"` / `button "Photo"` | 图片上传 | 打开文件选择器 |
| `button "视频"` / `button "Video"` | 视频上传 | 打开文件选择器 |
| `button "文档"` / `button "Document"` | 文档上传 | 上传 PDF 等文档 |
| `button "发布"` / `button "Post"` | 发布按钮 | 禁止自动点击 |

## 注意事项

- LinkedIn 帖子字数上限为 **3000 字符**
- 图片支持格式：JPG、PNG、GIF，单次最多 **9 张**
- 视频支持格式：MP4，最大 **5 GB**，时长最长 **10 分钟**
- 话题标签：直接在正文中输入 `#话题`，LinkedIn 会自动识别
- 帖子发布语言和界面语言一致，元素文字会随账号语言变化（中/英），需在 snapshot 后确认实际 ref
- 页面登录状态：如未登录，需先手动登录 LinkedIn，再执行此 workflow
- 严格遵守规则：最终只停留在编辑状态，由用户手动点击"发布"确认
