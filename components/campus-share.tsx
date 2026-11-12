import { useState, type RefObject } from 'react';
import { Download, Share2 } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { encodeShare } from '@/lib/campus/share';
import type { SceneController } from '@/lib/campus/types';

/** Share choices, with a manual copy field when the clipboard is unavailable. */
export function CampusShare({
  open,
  onOpenChange,
  ready,
  controller,
  pauseMotion,
  notify,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ready: boolean;
  controller: RefObject<SceneController | null>;
  pauseMotion: () => void;
  notify: (message: string, failed?: boolean) => void;
}) {
  const { t, locale } = useCampusLocale();
  const [link, setLink] = useState('');
  async function copyLink() {
    pauseMotion();
    const snapshot = controller.current?.getSnapshot();
    if (!snapshot) return;
    const url = new URL(location.pathname, location.origin);
    url.searchParams.set('lang', locale);
    url.hash = encodeShare(snapshot);
    try {
      await navigator.clipboard.writeText(url.href);
      notify('链接已复制');
    } catch {
      setLink(url.href);
    }
  }
  async function exportImage() {
    try {
      await controller.current?.exportImage();
      notify('图片已下载');
    } catch {
      notify('下载失败，请重试', true);
    }
  }
  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="share-dialog">
          <DialogTitle>{t('分享')}</DialogTitle>
          <div className="tools-grid">
            <button
              disabled={!ready}
              onClick={() => {
                onOpenChange(false);
                void copyLink();
              }}
            >
              <Share2 size={20} />
              {t('复制链接')}
            </button>
            <button
              disabled={!ready}
              onClick={() => {
                onOpenChange(false);
                void exportImage();
              }}
            >
              <Download size={20} />
              {t('下载图片')}
            </button>
          </div>
        </DialogContent>
      </Dialog>
      <Dialog
        open={Boolean(link)}
        onOpenChange={(value) => {
          if (!value) setLink('');
        }}
      >
        <DialogContent className="share-dialog">
          <DialogTitle>{t('复制链接')}</DialogTitle>
          <Input
            aria-label={t('视角链接')}
            value={link}
            readOnly
            onFocus={(event) => event.currentTarget.select()}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
