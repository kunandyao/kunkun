import {
  BarChart3,
  ChevronLeft, ChevronRight,
  Download,
  Film,
  HardDrive,
  Heart,
  Image as ImageIcon,
  Link,
  Loader2,
  MessageCircle,
  Music,
  Share2,
  X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { bridge } from '../services/bridge';
import { logger } from '../services/logger';
import { DouyinWork } from '../types';
import { withErrorHandling } from '../utils/errorHandler';
import { toast } from './Toast';
import { CommentAnalysisModal } from './CommentAnalysisModal';

/** 本地文件信息 */
interface LocalFileInfo {
  found: boolean;
  videoUrl?: string;
  imageUrls?: string[];
}

interface DetailModalProps {
  work: DouyinWork | null;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export const DetailModal: React.FC<DetailModalProps> = ({
  work, onClose, onPrev, onNext, hasPrev, hasNext
}) => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [localFile, setLocalFile] = useState<LocalFileInfo>({ found: false });
  const [isCheckingLocal, setIsCheckingLocal] = useState(false);
  const [isCrawlingComments, setIsCrawlingComments] = useState(false);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [lastCommentFile, setLastCommentFile] = useState<string | null>(null);

  // 检查本地文件
  const checkLocalFile = async (workId: string) => {
    setIsCheckingLocal(true);
    try {
      const result = await bridge.findLocalFile(workId);
      if (result.found) {
        if (result.video_path) {
          setLocalFile({
            found: true,
            videoUrl: bridge.getMediaUrl(result.video_path),
          });
        } else if (result.images && result.images.length > 0) {
          setLocalFile({
            found: true,
            imageUrls: result.images.map(p => bridge.getMediaUrl(p)),
          });
        }
      } else {
        setLocalFile({ found: false });
      }
    } catch {
      setLocalFile({ found: false });
    } finally {
      setIsCheckingLocal(false);
    }
  };

  useEffect(() => {
    setCurrentImageIndex(0);
    setLocalFile({ found: false });
    if (work) {
      checkLocalFile(work.id);
    }
  }, [work]);



  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') onPrev?.();
      if (e.key === 'ArrowRight') onNext?.();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, onPrev, onNext]);

  if (!work) return null;




  const copyLink = () => {
    navigator.clipboard.writeText(`https://www.douyin.com/video/${work.id}`);
    toast.success('链接已复制');
  };

  const crawlComments = async () => {
    if (!work) return;
    setIsCrawlingComments(true);
    try {
      const res = await bridge.crawlComments(work.id, 500);
      if (res.total > 0) {
        toast.success(`已爬取 ${res.total} 条评论${res.file ? '，已导出 CSV' : ''}`);
        if (res.file) {
          setLastCommentFile(res.file);
          const dir = res.file.replace(/[/\\][^/\\]+$/, '');
          bridge.openFolder(dir).catch(() => {});
        }
      } else {
        toast.info('该作品暂无评论或评论接口未返回数据');
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : '爬取评论失败';
      toast.error(msg);
      logger.error(`[DetailModal] 爬取评论失败: ${work.id} - ${e}`);
    } finally {
      setIsCrawlingComments(false);
    }
  };

  const crawlAndAnalyzeToDashboard = async () => {
    if (!work) return;
    setIsCrawlingComments(true);
    try {
      // 传递作品的标题和封面URL给后端（用于API限流时作为备选）
      const res = await bridge.crawlAndAnalyzeSingleWork(work.id, 200, work.desc, work.cover);
      if (res.success) {
        toast.success(`爬取并分析完成！共 ${res.total_comments} 条评论，已保存到数据大屏`);
        logger.success(`[DetailModal] 单个作品分析完成并保存到数据库: ${work.id}`);
      } else {
        toast.error(res.message || '分析失败');
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : '爬取并分析失败';
      toast.error(msg);
      logger.error(`[DetailModal] 爬取并分析失败: ${work.id} - ${e}`);
    } finally {
      setIsCrawlingComments(false);
    }
  };

  const openAnalysis = () => {
    if (lastCommentFile) {
      setShowAnalysisModal(true);
    } else {
      toast.info('请先爬取评论数据');
    }
  };

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    const maxIndex = (localFile.found && localFile.imageUrls ? localFile.imageUrls.length : work.images?.length) || 1;
    if (currentImageIndex < maxIndex - 1) {
      setCurrentImageIndex(prev => prev + 1);
    }
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (currentImageIndex > 0) {
      setCurrentImageIndex(prev => prev - 1);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl flex overflow-hidden w-[720px] h-[85vh] relative animate-in zoom-in-95 duration-200 border border-gray-200/50"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Left Side: Media */}
        <div className="flex-1 bg-black relative flex items-center justify-center group overflow-hidden">
          {hasPrev && (
            <button
              onClick={(e) => { e.stopPropagation(); onPrev?.(); }}
              className="absolute left-4 top-1/2 -translate-y-1/2 z-30 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-md transition-all opacity-0 group-hover:opacity-100 hover:scale-110"
            >
              <ChevronLeft size={24} />
            </button>
          )}
          {hasNext && (
            <button
              onClick={(e) => { e.stopPropagation(); onNext?.(); }}
              className="absolute right-4 top-1/2 -translate-y-1/2 z-30 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white backdrop-blur-md transition-all opacity-0 group-hover:opacity-100 hover:scale-110"
            >
              <ChevronRight size={24} />
            </button>
          )}

          {work.type === 'video' ? (
            localFile.found && localFile.videoUrl ? (
              <div className="relative w-full h-full flex items-center justify-center">
                <video
                  key={localFile.videoUrl}
                  src={localFile.videoUrl}
                  controls
                  autoPlay
                  loop
                  playsInline
                  className="max-w-full max-h-full w-auto h-auto object-contain"
                />
                <div className="absolute top-4 left-4 flex items-center gap-1.5 px-2 py-1 bg-green-500/90 text-white text-xs rounded-full backdrop-blur-sm">
                  <HardDrive size={12} />
                  本地文件
                </div>
              </div>
            ) : (
              <div 
                className="relative w-full h-full flex items-center justify-center"
                onDoubleClick={() => {
                  window.open(`https://www.douyin.com/video/${work.id}`, '_blank');
                }}
                title="双击跳转到抖音原视频"
              >
                <img src={work.cover} className="absolute inset-0 w-full h-full object-cover blur-sm opacity-30" alt="" />
                <img src={work.cover} className="relative max-w-full max-h-full object-contain z-10" alt="" />
                <div className="absolute inset-0 flex items-center justify-center z-20">
                  <div className="bg-black/60 backdrop-blur-md rounded-2xl p-6 max-w-[280px] text-center border border-white/10 shadow-2xl">
                    <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                      <Film size={24} className="text-white" />
                    </div>
                    <p className="text-white text-sm font-medium mb-2">视频暂无法在线播放</p>
                    <p className="text-white/60 text-xs mb-4">受跨域限制，请跳转到抖音观看</p>
                    <button
                      onClick={() => window.open(`https://www.douyin.com/video/${work.id}`, '_blank')}
                      className="w-full py-2.5 bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 rounded-lg text-white text-sm font-medium transition-all active:scale-95 shadow-lg"
                    >
                      跳转到抖音
                    </button>
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="relative w-full h-full flex items-center justify-center">
              {localFile.found && localFile.imageUrls && (
                <div className="absolute top-4 left-4 flex items-center gap-1.5 px-2 py-1 bg-green-500/90 text-white text-xs rounded-full backdrop-blur-sm z-10">
                  <HardDrive size={12} />
                  本地文件
                </div>
              )}
              <img
                src={
                  localFile.found && localFile.imageUrls
                    ? localFile.imageUrls[currentImageIndex] || work.cover
                    : work.images?.[currentImageIndex] || work.cover
                }
                className="max-w-full max-h-full object-contain"
                alt=""
              />

              {((localFile.found && localFile.imageUrls && localFile.imageUrls.length > 1) ||
                (work.images && work.images.length > 1)) && (
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-4 z-20">
                  <button
                    onClick={prevImage}
                    disabled={currentImageIndex === 0}
                    className="p-1.5 rounded-full bg-white/10 text-white hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all backdrop-blur-md border border-white/10"
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <span className="text-xs font-medium text-white/90 bg-black/40 px-3 py-1 rounded-full backdrop-blur-md border border-white/10 tabular-nums">
                    {currentImageIndex + 1} / {localFile.found && localFile.imageUrls ? localFile.imageUrls.length : work.images?.length || 0}
                  </span>
                  <button
                    onClick={nextImage}
                    disabled={currentImageIndex === ((localFile.found && localFile.imageUrls ? localFile.imageUrls.length : work.images?.length) || 1) - 1}
                    className="p-1.5 rounded-full bg-white/10 text-white hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all backdrop-blur-md border border-white/10"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>


        {/* Right Side: Info */}
        <div className="w-[300px] bg-white flex flex-col border-l border-gray-100 shrink-0">
          <div className="px-5 py-4 flex items-center justify-between border-b border-gray-100 bg-gray-50/30">
            <span className="font-bold text-gray-800">作品详情</span>
            <div className="flex items-center gap-1">
              <button
                onClick={copyLink}
                className="p-2 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-blue-600 transition-colors"
                title="复制链接"
              >
                <Link size={18} />
              </button>
              <div className="w-px h-4 bg-gray-200 mx-1"></div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-800 transition-colors"
                title="关闭"
              >
                <X size={20} />
              </button>
            </div>
          </div>

          <div className="px-5 py-4 flex items-center gap-3">
            <img src={work.author.avatar} className="w-10 h-10 rounded-full border border-gray-100" />
            <div className="min-w-0 flex-1">
              <div className="font-semibold text-sm truncate text-gray-900">{work.author.nickname}</div>
              <div className="text-xs text-gray-400 truncate">
                {work.author.unique_id
                  ? `@${work.author.unique_id}`
                  : work.author.short_id
                    ? `ID: ${work.author.short_id}`
                    : `UID: ${work.author.uid.substring(0, 20)}...`}
              </div>
            </div>
          </div>

          <div className="px-5 py-2 flex-1 overflow-y-auto custom-scrollbar">
            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{work.desc}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {work.desc.match(/#\S+/g)?.map((tag, i) => (
                <span key={i} className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded cursor-pointer hover:bg-blue-100">
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-4 text-xs text-gray-400 border-t border-gray-50 pt-3">
              发布于 {work.create_time}
            </div>
          </div>

          <div className="px-5 py-3 border-t border-gray-50 grid grid-cols-3 gap-2">
            <div className="flex flex-col items-center gap-1 text-gray-600 p-2 rounded-lg bg-gray-50">
              <Heart size={16} className={work.stats.digg_count > 0 ? "fill-red-500 text-red-500" : ""} />
              <span className="text-xs font-medium">{work.stats.digg_count}</span>
            </div>
            <div className="flex flex-col items-center gap-1 text-gray-600 p-2 rounded-lg bg-gray-50">
              <MessageCircle size={16} />
              <span className="text-xs font-medium">{work.stats.comment_count}</span>
            </div>
            <div className="flex flex-col items-center gap-1 text-gray-600 p-2 rounded-lg bg-gray-50">
              <Share2 size={16} />
              <span className="text-xs font-medium">{work.stats.share_count}</span>
            </div>
          </div>

          <div className="p-5 border-t border-gray-100 bg-gray-50/50 space-y-3">
            <div className="flex gap-2">
              <button
                onClick={crawlAndAnalyzeToDashboard}
                disabled={isCrawlingComments}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-lg text-xs font-medium hover:from-green-600 hover:to-emerald-700 transition-all active:scale-95 shadow-sm disabled:opacity-60"
              >
                {isCrawlingComments ? <Loader2 className="animate-spin" size={13} /> : <BarChart3 size={13} />}
                爬取&分析
              </button>

              <button
                onClick={() => window.open(`https://www.douyin.com/video/${work.id}`, '_blank')}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-50 hover:border-gray-300 transition-all active:scale-95 shadow-sm"
              >
                <Link size={14} />
                跳转到抖音
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 评论分析模态框 */}
      {showAnalysisModal && (
        <CommentAnalysisModal
          csvFile={lastCommentFile || undefined}
          onClose={() => setShowAnalysisModal(false)}
        />
      )}
    </div>
  );
};
