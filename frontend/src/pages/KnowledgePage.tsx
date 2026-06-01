import {
  Button,
  Card,
  Collapse,
  Drawer,
  Empty,
  Input,
  InputNumber,
  Segmented,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd';
import { isAxiosError } from 'axios';
import { useEffect, useMemo, useState } from 'react';
import {
  createKnowledge,
  deleteKnowledge,
  fetchKnowledge,
  importKnowledgeDocument,
  updateKnowledge,
} from '../api/knowledge';
import { KnowledgeForm, categories } from '../components/KnowledgeForm';
import { KnowledgeTable } from '../components/KnowledgeTable';
import type { ChunkingMethod, KnowledgeItem, KnowledgePayload } from '../types';

const chunkingOptions: { label: string; value: ChunkingMethod }[] = [
  { label: '固定长度', value: 'fixed_size' },
  { label: '按段落', value: 'paragraph' },
  { label: 'Markdown 标题', value: 'markdown_heading' },
  { label: '整篇文档', value: 'full_document' },
];

const chunkingMethodText: Record<string, string> = {
  fixed_size: '固定长度',
  paragraph: '按段落',
  markdown_heading: 'Markdown 标题',
  full_document: '整篇文档',
};

export function KnowledgePage() {
  const [items, setItems] = useState<KnowledgeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [importSource, setImportSource] = useState('上传文档');
  const [chunkingMethod, setChunkingMethod] = useState<ChunkingMethod>('fixed_size');
  const [chunkSize, setChunkSize] = useState(1200);
  const [chunkOverlap, setChunkOverlap] = useState(150);
  const [importing, setImporting] = useState(false);
  const [editing, setEditing] = useState<KnowledgeItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const knowledgeBaseGroups = useMemo(() => buildKnowledgeBaseGroups(items), [items]);
  const selectedGroup = useMemo(
    () => knowledgeBaseGroups.find((group) => group.category === selectedCategory) ?? null,
    [knowledgeBaseGroups, selectedCategory],
  );
  const selectedItems = useMemo(
    () => (selectedCategory ? items.filter((item) => item.category === selectedCategory) : []),
    [items, selectedCategory],
  );

  async function loadData() {
    setLoading(true);
    try {
      setItems(await fetchKnowledge());
    } catch (error) {
      messageApi.error('知识库加载失败，请确认后端服务已启动。');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  function openCreate() {
    setEditing(null);
    setDrawerOpen(true);
  }

  function openEdit(item: KnowledgeItem) {
    setEditing(item);
    setDrawerOpen(true);
  }

  async function handleSubmit(payload: KnowledgePayload) {
    setSubmitting(true);
    try {
      if (editing) {
        await updateKnowledge(editing.id, payload);
        messageApi.success('知识条目已更新');
      } else {
        await createKnowledge(payload);
        messageApi.success('知识条目已新增');
      }
      setDrawerOpen(false);
      await loadData();
    } catch (error) {
      messageApi.error('保存失败，请检查后端服务或表单内容。');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    await deleteKnowledge(id);
    messageApi.success('知识条目已删除');
    await loadData();
  }

  async function handleImport(file: File) {
    if (!selectedCategory) {
      messageApi.warning('请先进入一个知识库，再上传文档。');
      return;
    }

    setImporting(true);
    try {
      const result = await importKnowledgeDocument(file, {
        category: selectedCategory,
        source: importSource,
        chunking_method: chunkingMethod,
        chunk_size: chunkSize,
        chunk_overlap: chunkingMethod === 'full_document' ? 0 : chunkOverlap,
      });
      messageApi.success(`已导入 ${selectedCategory}：${result.filename}，共 ${result.imported_count} 个切片`);
      await loadData();
    } catch (error) {
      messageApi.error(getImportErrorMessage(error));
    } finally {
      setImporting(false);
    }
  }

  const drawerInitialValues = editing ?? (selectedCategory ? { category: selectedCategory } : undefined);

  return (
    <section className="workspace-panel">
      {contextHolder}
      <Space direction="vertical" size={18} className="full-width">
        <div className="page-heading">
          <div>
            <Typography.Title level={2}>{selectedCategory ?? '校园知识库管理'}</Typography.Title>
            <Typography.Text type="secondary">
              {selectedCategory
                ? '在当前知识库中上传文档、选择分块方式，并查看文档切片。'
                : '先进入一个知识库，再上传文档进行分块建库。'}
            </Typography.Text>
          </div>
          <Space wrap>
            {selectedCategory ? <Button onClick={() => setSelectedCategory(null)}>返回知识库</Button> : null}
            <Button onClick={() => void loadData()}>刷新</Button>
            <Button type="primary" onClick={openCreate}>
              新增知识
            </Button>
          </Space>
        </div>

        {selectedCategory && selectedGroup ? (
          <KnowledgeBaseDetail
            group={selectedGroup}
            selectedItems={selectedItems}
            importSource={importSource}
            chunkingMethod={chunkingMethod}
            chunkSize={chunkSize}
            chunkOverlap={chunkOverlap}
            importing={importing}
            loading={loading}
            onImportSourceChange={setImportSource}
            onChunkingMethodChange={setChunkingMethod}
            onChunkSizeChange={setChunkSize}
            onChunkOverlapChange={setChunkOverlap}
            onImport={handleImport}
            onEdit={openEdit}
            onDelete={handleDelete}
          />
        ) : (
          <KnowledgeBaseList
            groups={knowledgeBaseGroups}
            loading={loading}
            onSelect={(category) => setSelectedCategory(category)}
          />
        )}
      </Space>

      <Drawer
        title={editing ? '编辑知识条目' : '新增知识条目'}
        open={drawerOpen}
        width={520}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose
      >
        <KnowledgeForm
          initialValues={drawerInitialValues}
          submitting={submitting}
          onSubmit={handleSubmit}
          onCancel={() => setDrawerOpen(false)}
        />
      </Drawer>
    </section>
  );
}

interface KnowledgeBaseListProps {
  groups: KnowledgeBaseGroup[];
  loading: boolean;
  onSelect: (category: string) => void;
}

function KnowledgeBaseList({ groups, loading, onSelect }: KnowledgeBaseListProps) {
  return (
    <Card className="knowledge-base-list" loading={loading}>
      <div className="knowledge-base-list-heading">
        <div>
          <Typography.Title level={4}>选择知识库</Typography.Title>
          <Typography.Text type="secondary">进入对应知识库后，再上传文档并选择分块方法。</Typography.Text>
        </div>
        <Tag color="green">{groups.length} 个知识库</Tag>
      </div>
      <div className="knowledge-base-grid">
        {groups.map((group) => (
          <Card
            key={group.category}
            hoverable
            className="knowledge-base-card"
            role="button"
            tabIndex={0}
            onClick={() => onSelect(group.category)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelect(group.category);
              }
            }}
          >
            <div className="knowledge-base-card-header">
              <Tag color={group.chunkCount > 0 ? 'green' : 'default'}>{group.category}</Tag>
              <Typography.Text strong>{group.category}</Typography.Text>
            </div>
            <div className="knowledge-base-card-stats">
              <span>
                <strong>{group.documents.length}</strong>
                <small>文档</small>
              </span>
              <span>
                <strong>{group.chunkCount}</strong>
                <small>切片</small>
              </span>
            </div>
            <Button type="link" className="knowledge-base-enter">
              进入知识库
            </Button>
          </Card>
        ))}
      </div>
    </Card>
  );
}

interface KnowledgeBaseDetailProps {
  group: KnowledgeBaseGroup;
  selectedItems: KnowledgeItem[];
  importSource: string;
  chunkingMethod: ChunkingMethod;
  chunkSize: number;
  chunkOverlap: number;
  importing: boolean;
  loading: boolean;
  onImportSourceChange: (value: string) => void;
  onChunkingMethodChange: (value: ChunkingMethod) => void;
  onChunkSizeChange: (value: number) => void;
  onChunkOverlapChange: (value: number) => void;
  onImport: (file: File) => Promise<void>;
  onEdit: (item: KnowledgeItem) => void;
  onDelete: (id: number) => Promise<void>;
}

function KnowledgeBaseDetail({
  group,
  selectedItems,
  importSource,
  chunkingMethod,
  chunkSize,
  chunkOverlap,
  importing,
  loading,
  onImportSourceChange,
  onChunkingMethodChange,
  onChunkSizeChange,
  onChunkOverlapChange,
  onImport,
  onEdit,
  onDelete,
}: KnowledgeBaseDetailProps) {
  return (
    <>
      <Card className="knowledge-base-summary">
        <div>
          <Tag color="green">当前知识库</Tag>
          <Typography.Title level={3}>{group.category}</Typography.Title>
          <Typography.Text type="secondary">上传文档会固定写入该知识库，并在下方按文档展示切片。</Typography.Text>
        </div>
        <div className="knowledge-base-summary-stats">
          <span>
            <strong>{group.documents.length}</strong>
            <small>文档</small>
          </span>
          <span>
            <strong>{group.chunkCount}</strong>
            <small>切片</small>
          </span>
        </div>
      </Card>

      <Card className="import-panel">
        <div className="import-panel-grid">
          <div>
            <Typography.Title level={4}>上传文档并选择分块方法</Typography.Title>
            <Typography.Text type="secondary">
              目标知识库：{group.category}。支持 PDF、Word .docx、Markdown。
            </Typography.Text>
          </div>
          <Input
            className="source-input"
            value={importSource}
            onChange={(event) => onImportSourceChange(event.target.value)}
            placeholder="来源"
          />
        </div>
        <div className="chunk-control-grid">
          <div className="chunk-control-item wide">
            <Typography.Text strong>分块方法</Typography.Text>
            <Segmented
              block
              value={chunkingMethod}
              options={chunkingOptions}
              onChange={(value) => onChunkingMethodChange(value as ChunkingMethod)}
            />
          </div>
          <div className="chunk-control-item">
            <Typography.Text strong>切片大小</Typography.Text>
            <InputNumber
              min={100}
              max={5000}
              step={100}
              value={chunkSize}
              disabled={chunkingMethod === 'full_document'}
              onChange={(value) => onChunkSizeChange(Number(value ?? 1200))}
              addonAfter="字"
            />
          </div>
          <div className="chunk-control-item">
            <Typography.Text strong>重叠长度</Typography.Text>
            <InputNumber
              min={0}
              max={Math.max(0, chunkSize - 1)}
              step={50}
              value={chunkOverlap}
              disabled={chunkingMethod === 'full_document'}
              onChange={(value) => onChunkOverlapChange(Number(value ?? 0))}
              addonAfter="字"
            />
          </div>
        </div>
        <Upload.Dragger
          className="document-uploader"
          accept=".pdf,.docx,.md,.markdown"
          multiple={false}
          showUploadList={false}
          disabled={importing}
          beforeUpload={(file) => {
            void onImport(file as File);
            return Upload.LIST_IGNORE;
          }}
        >
          <Typography.Text strong>{importing ? '正在导入文档...' : '点击或拖拽文档到这里上传'}</Typography.Text>
          <br />
          <Typography.Text type="secondary">
            上传到：{group.category}；当前分块方法：{chunkingMethodText[chunkingMethod]}
          </Typography.Text>
        </Upload.Dragger>
      </Card>

      <Card className="chunk-browser" title={`${group.category} 的文档切片`}>
        {group.documents.length === 0 ? (
          <Empty description="该知识库还没有文档。请先在上方上传 PDF、Word 或 Markdown。" />
        ) : (
          <Collapse
            items={group.documents.map((document) => ({
              key: `${group.category}-${document.documentName}`,
              label: (
                <Space wrap>
                  <Typography.Text strong>{document.documentName}</Typography.Text>
                  <Tag>{document.source}</Tag>
                  <Typography.Text type="secondary">{document.items.length} 个切片</Typography.Text>
                </Space>
              ),
              children: (
                <Space direction="vertical" className="full-width">
                  {document.documentPath ? (
                    <Typography.Text type="secondary">本地文件：{document.documentPath}</Typography.Text>
                  ) : null}
                  <div className="chunk-list">
                    {document.items.map((item) => (
                      <div className="chunk-card" key={item.id}>
                        <Space wrap className="chunk-card-meta">
                          <Tag color="cyan">
                            切片 {item.chunk_index ?? 1}/{item.chunk_total ?? document.items.length}
                          </Tag>
                          <Tag color="blue">
                            {chunkingMethodText[item.chunking_method ?? ''] ?? item.chunking_method ?? '手工录入'}
                          </Tag>
                          <Typography.Text strong>{item.title}</Typography.Text>
                        </Space>
                        <Typography.Paragraph ellipsis={{ rows: 4, expandable: true }}>
                          {item.content}
                        </Typography.Paragraph>
                      </div>
                    ))}
                  </div>
                </Space>
              ),
            }))}
          />
        )}
      </Card>

      <Card className="knowledge-table-card" title={`${group.category} 的知识条目`}>
        <KnowledgeTable data={selectedItems} loading={loading} onEdit={onEdit} onDelete={onDelete} />
      </Card>
    </>
  );
}

function getImportErrorMessage(error: unknown) {
  if (isAxiosError<{ detail?: unknown }>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          if (typeof item === 'object' && item !== null && 'msg' in item) {
            return String((item as { msg?: unknown }).msg);
          }
          return String(item);
        })
        .join('；');
    }
  }
  return '文档导入失败，请确认文件格式为 PDF、Word 或 Markdown。';
}

interface DocumentGroup {
  documentName: string;
  source: string;
  documentPath: string | null;
  items: KnowledgeItem[];
}

interface KnowledgeBaseGroup {
  category: string;
  documents: DocumentGroup[];
  chunkCount: number;
}

function buildKnowledgeBaseGroups(items: KnowledgeItem[]): KnowledgeBaseGroup[] {
  const categoryMap = new Map<string, Map<string, KnowledgeItem[]>>();
  for (const category of categories) {
    categoryMap.set(category, new Map());
  }

  for (const item of items) {
    const category = item.category || '未分类';
    const documentName = item.document_name || item.source || '手工录入';
    if (!categoryMap.has(category)) {
      categoryMap.set(category, new Map());
    }
    const documentMap = categoryMap.get(category)!;
    if (!documentMap.has(documentName)) {
      documentMap.set(documentName, []);
    }
    documentMap.get(documentName)!.push(item);
  }

  const categoryOrder = new Map(categories.map((category, index) => [category, index]));
  return Array.from(categoryMap.entries())
    .sort(([left], [right]) => {
      const leftOrder = categoryOrder.get(left) ?? Number.MAX_SAFE_INTEGER;
      const rightOrder = categoryOrder.get(right) ?? Number.MAX_SAFE_INTEGER;
      return leftOrder - rightOrder || left.localeCompare(right, 'zh-CN');
    })
    .map(([categoryName, documentMap]) => {
      const documents = Array.from(documentMap.entries())
        .sort(([left], [right]) => left.localeCompare(right, 'zh-CN'))
        .map(([documentName, documentItems]) => {
          const sortedItems = [...documentItems].sort(
            (left, right) => (left.chunk_index ?? left.id) - (right.chunk_index ?? right.id),
          );
          return {
            documentName,
            source: sortedItems[0]?.source ?? '未知来源',
            documentPath: sortedItems[0]?.document_path ?? null,
            items: sortedItems,
          };
        });
      return {
        category: categoryName,
        documents,
        chunkCount: documents.reduce((sum, document) => sum + document.items.length, 0),
      };
    });
}
