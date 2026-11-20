---
title: Manticore Search介绍和总结
slug: introduction-and-summary-of-manticore-search-ok4gh
url: /post/introduction-and-summary-of-manticore-search-ok4gh.html
date: '2026-11-17 16:28:03+08:00'
lastmod: '2026-11-20 09:33:19+08:00'
toc: true
isCJKLanguage: true
---





## Manticore Search介绍

[https://github.com/manticoresoftware/manticoresearch](https://github.com/manticoresoftware/manticoresearch)

Manticore Search 这东西我好像提过,但是现在正式写一篇吧,这个是个全文检索数据库,是根据老版本的Sphinx重写的.你如果去看他的主页,就会看到一堆堆的功能,以及多的爆棚的性能比较.不过这东西确实也很强,也非常好用.

我用这个主要是当时找地名地址库,找的想吐血, [Nominatim](https://github.com/osm-search/Nominatim) Pelias photon libpostal 都找过一遍,也尝试过部署,但是发现,要么就是部署困难,要么就是磁盘占用非常大,要么就是数据格式有严格要求,导入外部数据困难,要么不支持模糊查询/查询功能特别弱,要么是中文查询有问题...

后来翻到了这个,非常适合我们的项目,

1. 原生支持地理位置（地理空间）查询,它是支持球面距离的,只要扔进去经纬度坐标即可
2. 模糊查询支持非常好,中文支持也很好,甚至直接支持结巴分词
3. 部署简单,可以直接docker部署
4. 建表简单,查询简单,而且接口丰富,可以用http或者mysql语法,方便接入
5. 导入简单,因为建表实际就是类似Mysql的表,数据可以直接插入

大致说一下它的部署和使用吧:

## 部署

挺简单的,官方维护了Docker镜像,直接从DockerHub上拉取就行

```bash
docker pull manticoresearch/manticore:latest
docker run --name manticore --rm -d manticoresearch/manticore && until docker logs manticore 2>&1 | grep -q "accepting connections"; do sleep 1; done && docker exec -it manticore mysql && docker stop manticore
```

启动后进入docker的命令行里,就跟mysql一样,可以建表了,默认是实时表,这个看你的数据量,我的数据量反正是到不了单表极限的,文档里:单表磁盘体积建议控制在 50GB \~ 100GB 以内,大概是千万级到亿级别的表,普通表是只读表,只能用配置文件建和插入,比较麻烦.不过如果你数据真的是只读的(其实理论上地名地址应该是只读,但是对吧,甲方需求...)普通表压缩率和结构比实时表高效 ,因此可以高半个到一个数量级.正常情况下够用了,实在不行可以上分布式表,那个可以自己去研究文档

```sql
CREATE TABLE places (
    id bigint,
    name text,
    address text,
    abbr text,
    lat float,
    lon float
) min_infix_len='2' charset_table='chinese, a..z, A..Z, 0..9' morphology='jieba_chinese';

```

看起来跟普通的SQL有点不同,主要是表有设置,参考  [3️⃣ Creating a table > Creating a local table > Plain and real-time table settings | Manticore Search Manual](https://manual.manticoresearch.com/Creating_a_table/Local_tables/Plain_and_real-time_table_settings) 文档,我是用于地名地址的,所以搜索把特殊符号和空格忽略,然后默认用结巴分词作为分词器,否则默认是一个字一个字的拆分,也可以用ICU拆.,具体的其他的看文档吧

剩下的你就直接用SQL插入数据就完了,类似如下:

```sql
INSERT INTO places (id, name, address, abbr, lat, lon) VALUES
(1, '北京天安门', '北京市东城区东长安街', 'TAM', 39.908722, 116.397499),
(2, '北京故宫博物院', '北京市东城区景山前街4号', 'GG', 39.916345, 116.397155),
(3, '北京南站', '北京市丰台区永外大街车站路12号', 'BJN', 39.865195, 116.378517);

```

## 操作

Manticore Search最友好的是有Http接口,级别都是Post操作,可以直接批量增删改查,具体文档参考[OpenAPI specification | Manticore Search Manual](https://manual.manticoresearch.com/Openapi)那一节,或者看看 [OpenAPI 规范 | Manticore Search Manual](https://manual.manticoresearch.com/zh/Openapi)  这个有个机器可读的规范,我建议是直接给AI吧

这是http接口,也可以直接进入mysql里,直接操作表,那个就是直接进入docker操作了,跟sql语法基本一致.

其实如果只需要简单的增删改查,可以直接用http的sql接口,查询直接用sql,

```bash
curl.exe -X POST http://127.0.0.1:9308/sql -d "select * from places order by id desc  LIMIT 5;"
```

如果要修改,加上 mode\=raw 参数即可,例如:

```bash
curl.exe -X POST "http://127.0.0.1:9308/sql?mode=raw" -d "DELETE FROM places WHERE id IN (1,2);"
```

‍

### 自动补全

Manticore 跟Sphinx一样支持全文检索,因此,也扩展了一些语法,具体参考 https://manual.manticoresearch.com/Searching/Spell_correction#SQL, 举一下例子:

```sql

-- 自动补全
CALL AUTOCOMPLETE('query_beginning', 'table', [...options]);
# example
mysql> CALL AUTOCOMPLETE('劳动','poi_index');
+--------------+
| query        |
+--------------+
| 劳动         |
| 劳动者       |
| 劳动力       |
| 劳动局       |
| 劳动党       |
| 劳动报       |
| 劳动法       |
| 劳动保护     |
| 劳动就业     |
| 劳动人事     |
+--------------+


-- 拼写矫正,主要是根据键盘配列矫正,所以中文不支持
SELECT
  ...
  MATCH('...')
  ...
  OPTION fuzzy={0|1}
  [, distance=N]
  [, preserve={0|1}]
  [, layouts='{be,bg,br,ch,de,dk,es,fr,uk,gr,it,no,pt,ru,se,ua,us}']
}
```

### 排名器

- ​`proximity_bm25`，默认的排名模式，同时使用并结合了短语接近度和BM25排名。
- ​`bm25`，一种只使用BM25的统计排名模式（类似大多数其他全文引擎）。该模式速度更快，但对于包含多个关键词的查询可能导致质量较差。
- ​`none`，无排名模式。该模式显然最快。所有匹配项均赋值权重1。有时称为布尔搜索，只匹配文档但不排序。
- ​`wordcount`，按关键词出现次数排名。该排名器计算每个字段的关键词出现次数，再乘以字段权重，最后求和。
- ​`proximity`​ 返回原始的短语接近值作为结果。该模式在内部用于模拟 `SPH_MATCH_ALL` 查询。
- ​`matchany`​ 返回在早期 `SPH_MATCH_ANY`​ 模式中计算的排名值，并在内部用于模拟 `SPH_MATCH_ANY` 查询。
- ​`fieldmask` 返回一个32位掩码，第N位对应第N个全文字段，编号从0开始。只有当相应字段含有满足查询的关键词出现时，该位才会被置位。
- ​`sph04`​ 基本上基于默认的 `proximity_bm25`​ 排名器，但额外提升当匹配发生在文本字段开头或结尾的情况。因此，如果某字段完全等于查询，`sph04` 应该将其排名高于包含该查询但不完全相等的字段。（例如，当查询为“Hyde Park”时，标题为“Hyde Park”的文档应排名高于标题为“Hyde Park, London”或“The Hyde Park Cafe”的文档。）
- ​`expr`​ 允许你在运行时指定排名公式。它暴露了多个内部文本因素，允许你定义如何从这些因素计算最终权重。你可以在[下方小节](https://manual.manticoresearch.com/zh/Searching/Sorting_and_ranking#Quick-summary-of-the-ranking-factors)中找到其语法细节和可用因素参考。

排名器名称不区分大小写。示例：

```sql
SELECT ... OPTION ranker=sph04;
```

### 全文检索

所有全文搜索都靠 `MATCH('...')`​ 触发，它会对查询字符串应用**与建表时相同的分词设置**，再拿分词后的词项去匹配索引中的词项。**运算符页面**：在 `MATCH('...')`​ 的字符串内部，可以用特定符号控制词与词之间“必须同时出现”“出现任意一个”“允许错几个字”等规则。每条 `SELECT`​ 最多一个 `MATCH()`。查询串会先用**与建表时完全相同的分词规则**切分，再拿切出来的词项去匹配索引中的词项。

> **基本用法**回答“搜索从哪里发起”——用 `WHERE MATCH('...')`​；  
> **运算符**回答“`MATCH` 字符串里面能怎么写”——字段限制、短语、Quorum、邻近、通配符等。

‍

|类别|运算符 / 语法|一句话|
| :---------| :----------------------------------------| :-------------------------------|
|布尔|​`词1 词2`​（隐式 AND）、`\|`​（OR）、`MAYBE`​、`-词`​ / `!词`|控制词的命中组合|
|字段|​`@字段`​、`@(字段1,字段2)`​、`@!字段`​、`@*`​、`@字段[N]`|控制搜索范围|
|短语|​`"词1 词2"`|词必须相邻|
|邻近|​`"词1 词2"~N`|允许词间插入，总跨度 ≤N|
|Quorum|​`"词1 词2 词3"/N`​ 或 `/0.x`|至少命中 N 个或 x% 的词|
|通配符|​`词*`​、`*词`​、`*词*`​、`词?词`|词典词项展开（需 `min_infix_len`​ / `min_prefix_len`）|
|正则|​`REGEX(/.../)`|RE2 语法，扫描词典，性能开销大|
|顺序|​`<<`|强制词序|
|位置|​`^`​、`$`|字段开头 / 结尾|
|精确词形|​`=词`|不还原词干（需 `index_exact_words`）|

‍

示例:

```sql
SELECT id, name FROM places WHERE MATCH('北京');

-- 北京 且 南站（隐式 AND）
SELECT * FROM places WHERE MATCH('北京 南站');

-- 故宫 或 天安门
SELECT * FROM places WHERE MATCH('故宫 | 天安门');

-- 北京相关，但排除“南站”
SELECT * FROM places WHERE MATCH('北京 -南站');

-- 只在 name 字段找“北京”
SELECT * FROM places WHERE MATCH('@name 北京');

-- 在 name 和 abbr 两个字段里找“TAM”
SELECT * FROM places WHERE MATCH('@(name,abbr) TAM');

SELECT * FROM places WHERE MATCH('"北京 南站"');

-- “北京”和“博物院”之间最多隔 2 个词（总跨度 ≤3）
SELECT * FROM places WHERE MATCH('"北京 博物院"~3');

-- 3 个词中至少命中 2 个
SELECT * FROM places WHERE MATCH('"北京 故宫 博物院"/2');

-- 3 个词中至少命中 50%（即 ≥2 个）
SELECT * FROM places WHERE MATCH('"北京 故宫 博物院"/0.5');

-- 匹配以“北京”开头的词项
SELECT * FROM places WHERE MATCH('北京*');

-- 匹配包含“天安”的词项（中缀，依赖 min_infix_len）
SELECT * FROM places WHERE MATCH('*天安*');

-- 匹配“南”和“站”之间隔一个任意字符的词项
SELECT * FROM places WHERE MATCH('南?站');

-- 匹配“故”和“宫”之间隔一个任意字符
SELECT * FROM places WHERE MATCH('"REGEX(/故.宫/)"');

-- 匹配“北京”后跟任意内容
SELECT * FROM places WHERE MATCH('"REGEX(/北京.*/)"');

-- “北京”必须出现在 name 字段开头
SELECT * FROM places WHERE MATCH('@name ^北京');

-- “站”必须出现在 name 字段末尾
SELECT * FROM places WHERE MATCH('@name 站$');

-- “天安门”必须按这个顺序出现
SELECT * FROM places WHERE MATCH('天安门 << 北京');

-- 1）字段 + 布尔：只在 name 和 abbr 里找，排除 address
SELECT id, name FROM places
WHERE MATCH('@(name,abbr) 北京 -南站');

-- 2）短语 + 邻近：两个词之间允许隔词
SELECT id, name FROM places
WHERE MATCH('"北京 博物院"~3');

-- 3）Quorum：三个词命中两个就算
SELECT id, name FROM places
WHERE MATCH('"北京 故宫 南站"/2');

-- 4）通配符：中缀展开（依赖 min_infix_len='2'）
SELECT id, name FROM places
WHERE MATCH('*天安*');

-- 5）REGEX：正则直接写在 MATCH 引号内
SELECT id, name FROM places
WHERE MATCH('"REGEX(/天.?门/)"');

-- 6）顺序：强制“天安门”在“北京”之前
SELECT id, name FROM places
WHERE MATCH('天安门 << 北京');
```
