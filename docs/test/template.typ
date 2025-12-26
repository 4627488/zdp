// template.typ
// 定义全局字体变量，方便替换
#let font-song = ("SimSun", "Songti SC", "Noto Serif CJK SC")
#let font-hei = ("SimHei", "Heiti SC", "Noto Sans CJK SC")
#let font-main-size = 12pt

// 核心文档模板函数
#let doc-template(
  doc-id: "DOCUMENT-ID",
  title: "文档标题",
  org-name: "ZDP软件项目组", // 封面底部公司名称
  doc-type: "XX软件配置项测试报告", // 封面中间的小字描述
  body,
) = {
  // 1. 全局设置
  set text(font: font-song, size: font-main-size, lang: "zh")
  set heading(numbering: "1.1")

  // 标题样式：黑体
  show heading: it => {
    set text(font: font-hei, weight: "bold")
    block(above: 1.5em, below: 1em, it)
  }

  // 2. 页眉页脚设置
  set page(
    paper: "a4",
    margin: (x: 2.5cm, y: 2.5cm),
    header: [
      #set text(size: 10pt)
      #align(right)[#doc-id]
      #line(length: 100%, stroke: 0.5pt)
    ],
    footer: context [
      #set text(size: 10pt)
      #line(length: 100%, stroke: 0.5pt)
      // 实现 "共 X 页 第 Y 页" 格式
      #let total = counter(page).final().at(0)
      #let current = counter(page).get().at(0)
      #align(center)[共 #total 页 #h(1em) 第 #current 页]
    ],
  )

  // 3. 绘制封面
  // 封面单独一页，不显示页眉页脚
  page(header: none, footer: none)[
    #set text(size: 10.5pt)

    // 右上角文档编号
    #place(top + right)[#doc-id]
    #v(1em)

    // 顶部修改记录表格
    #align(left)[
      #table(
        columns: (1fr, 1fr, 2fr, 1fr, 1.5fr),
        rows: (2.5em, 2.5em),
        align: center + horizon,
        fill: (_, row) => if row == 0 { gray.lighten(90%) },
        [标记], [数量], [修改单号], [签字], [日期],
        [], [], [], [], [],
        // 空行供手写
      )
    ]

    #v(4em)

    // 标题区域
    #align(center)[
      #text(font: font-hei, size: 22pt, weight: "bold")[#title]
      #v(1em)
      #text(size: 14pt)[(#doc-type)]
    ]

    #v(1fr) // 弹性空白，将签署区推到底部

    // 底部签署区 (左右两栏布局)
    #grid(
      columns: (1fr, 1fr),
      gutter: 2em,
      align(left)[
        #set text(size: 12pt)
        #table(
          columns: (auto, 1fr),
          stroke: none,
          row-gutter: 1.5em,
          [编制：], [#line(length: 100%, stroke: 0.5pt)],
          [校对：], [#line(length: 100%, stroke: 0.5pt)],
          [审核：], [#line(length: 100%, stroke: 0.5pt)],
          [会签：], [#line(length: 100%, stroke: 0.5pt)],
        )
      ],
      align(left)[ // 右侧栏
        #set text(size: 12pt)
        #table(
          columns: (auto, 1fr),
          stroke: none,
          row-gutter: 1.5em,
          [会签：], [#line(length: 100%, stroke: 0.5pt)],
          [标检：], [#line(length: 100%, stroke: 0.5pt)],
          [批准：], [#line(length: 100%, stroke: 0.5pt)],
          [], [],
          // 占位保持对齐
        )
      ],
    )

    #v(2em)
    #align(center)[
      #text(font: font-hei, size: 15pt)[#org-name]
    ]
    #v(1cm)
  ]

  // 4. 目录
  pagebreak()
  show outline.entry: it => {
    v(12pt, weak: true)
    it
  }
  outline(title: "目 次", indent: auto)
  pagebreak()

  // 5. 正文内容
  body
}

// 辅助函数：统一样式的表格
#let std-table(columns: auto, caption: none, ..content) = {
  figure(
    table(
      columns: columns,
      align: center + horizon,
      stroke: 0.5pt,
      ..content
    ),
    caption: caption,
  )
}
