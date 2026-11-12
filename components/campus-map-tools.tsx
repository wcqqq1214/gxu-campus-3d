import { useSyncExternalStore, type ComponentProps } from 'react';
import { Tooltip } from '@base-ui/react/tooltip';
import {
  CircleHelp,
  Ellipsis,
  Expand,
  Grid2X2,
  House,
  Minus,
  Navigation,
  Plus,
  ScanEye,
  Share2,
} from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import type { CameraStore } from '@/lib/campus/camera-store';
import { cameraBearing } from '@/lib/campus/share';
import type { SceneController } from '@/lib/campus/types';

export type MapView = Parameters<SceneController['view']>[0];

/** View controls beside the map; narrow layouts move most of them into a dialog. */
export function CampusMapTools({
  camera,
  ready,
  onView,
  onFullscreen,
  onShare,
  onMore,
}: {
  camera: CameraStore;
  ready: boolean;
  onView: (view: MapView) => void;
  onFullscreen: () => void;
  onShare: () => void;
  onMore: () => void;
}) {
  const { t } = useCampusLocale();
  return (
    <Tooltip.Provider delay={200}>
      <div className="map-tools" aria-label={t('视角控制')}>
        <MapToolButton
          className="north-button"
          onClick={() => onView('north')}
          aria-label={t('朝向正北')}
          tooltip={t('朝向正北')}
        >
          <NorthArrow camera={camera} />
          <span>N</span>
        </MapToolButton>
        <div className="tool-stack zoom-tools">
          <MapToolButton
            onClick={() => onView('zoomIn')}
            aria-label={t('放大')}
            tooltip={t('放大')}
            shortcut="+"
          >
            <Plus size={19} />
          </MapToolButton>
          <MapToolButton
            onClick={() => onView('zoomOut')}
            aria-label={t('缩小')}
            tooltip={t('缩小')}
            shortcut="−"
          >
            <Minus size={19} />
          </MapToolButton>
        </div>
        <div className="tool-stack secondary-tools">
          <MapToolButton
            onClick={() => onView('top')}
            aria-label={t('俯视')}
            tooltip={t('俯视')}
          >
            <Grid2X2 size={18} />
          </MapToolButton>
          <MapToolButton
            onClick={() => onView('tilt')}
            aria-label={t('鸟瞰')}
            tooltip={t('鸟瞰')}
          >
            <ScanEye size={18} />
          </MapToolButton>
          <MapToolButton
            onClick={() => onView('overview')}
            aria-label={t('回到全景')}
            tooltip={t('回到全景')}
            shortcut="Home"
          >
            <House size={18} />
          </MapToolButton>
          <MapToolButton
            aria-label={t('全屏')}
            tooltip={t('全屏')}
            onClick={onFullscreen}
          >
            <Expand size={18} />
          </MapToolButton>
          <MapToolButton
            aria-label={t('分享')}
            tooltip={t('分享')}
            disabled={!ready}
            onClick={onShare}
          >
            <Share2 size={18} />
          </MapToolButton>
        </div>
        <div className="tool-stack mobile-tools">
          <MapToolButton
            className="mobile-reset"
            onClick={() => onView('overview')}
            aria-label={t('回到全景')}
            tooltip={t('回到全景')}
            shortcut="Home"
          >
            <House size={18} />
          </MapToolButton>
          <MapToolButton
            className="more-tools-button"
            onClick={onMore}
            aria-haspopup="dialog"
            aria-label={t('更多工具')}
            tooltip={t('更多工具')}
          >
            <Ellipsis size={20} />
            <span>{t('更多')}</span>
          </MapToolButton>
        </div>
      </div>
    </Tooltip.Provider>
  );
}

/** The narrow-layout tool menu. Each action closes it first. */
export function CampusMoreTools({
  open,
  onOpenChange,
  ready,
  onView,
  onFullscreen,
  onShare,
  onHelp,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ready: boolean;
  onView: (view: MapView) => void;
  onFullscreen: () => void;
  onShare: () => void;
  onHelp: () => void;
}) {
  const { t } = useCampusLocale();
  const close = (action: () => void) => () => {
    onOpenChange(false);
    action();
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="tools-dialog">
        <DialogTitle>{t('更多工具')}</DialogTitle>
        <div className="tools-grid">
          <button onClick={close(() => onView('overview'))}>
            <House size={20} />
            {t('回到全景')}
          </button>
          <button onClick={close(() => onView('north'))}>
            <Navigation size={20} />
            {t('朝向正北')}
          </button>
          <button onClick={close(() => onView('top'))}>
            <Grid2X2 size={20} />
            {t('俯视')}
          </button>
          <button onClick={close(() => onView('tilt'))}>
            <ScanEye size={20} />
            {t('鸟瞰')}
          </button>
          <button onClick={close(onFullscreen)}>
            <Expand size={20} />
            {t('全屏')}
          </button>
          <button disabled={!ready} onClick={close(onShare)}>
            <Share2 size={20} />
            {t('分享')}
          </button>
          <button onClick={close(onHelp)}>
            <CircleHelp size={20} />
            {t('操作说明')}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function CampusHelp({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { t } = useCampusLocale();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="tools-dialog">
        <DialogTitle>{t('操作说明')}</DialogTitle>
        <dl className="gesture-instructions">
          <dt>{t('触屏')}</dt>
          <dd>{t('单指拖动旋转，双指拖动平移，双指捏合缩放')}</dd>
          <dt>{t('鼠标与触控板')}</dt>
          <dd>{t('拖动旋转，右键拖动平移，滚轮缩放')}</dd>
          <dt>{t('键盘')}</dt>
          <dd>
            {t(
              'Tab 切换控件，Enter 确认；选中地图后，方向键平移，+ 和 − 缩放，Home 回到全景',
            )}
          </dd>
          <dt>{t('搜索')}</dt>
          <dd>{t('支持名称和简称，如“六教”')}</dd>
          <dt>{t('游览')}</dt>
          <dd>{t('拖动地图即可暂停')}</dd>
        </dl>
      </DialogContent>
    </Dialog>
  );
}

/** Follows camera samples without re-rendering the surrounding map controls. */
function NorthArrow({ camera }: { camera: CameraStore }) {
  // A primitive selection skips renders for samples that only pan or zoom.
  const bearing = useSyncExternalStore(
    camera.subscribe,
    () => cameraBearing(camera.get()),
    () => cameraBearing(null),
  );
  return (
    <Navigation size={20} style={{ transform: `rotate(${bearing - 45}deg)` }} />
  );
}
function MapToolButton({
  tooltip,
  shortcut,
  ...props
}: ComponentProps<'button'> & { tooltip: string; shortcut?: string }) {
  return (
    <Tooltip.Root disabled={props.disabled}>
      <Tooltip.Trigger render={<button {...props} />} />
      <Tooltip.Portal>
        <Tooltip.Positioner
          className="map-tool-tooltip-positioner"
          side="left"
          sideOffset={10}
        >
          <Tooltip.Popup className="map-tool-tooltip">
            {tooltip}
            {shortcut && <kbd>{shortcut}</kbd>}
          </Tooltip.Popup>
        </Tooltip.Positioner>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
