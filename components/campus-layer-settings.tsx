import {
  Building2,
  Dumbbell,
  Layers3,
  Navigation,
  RectangleEllipsis,
  Scan,
  Trees,
  Waves,
} from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { Switch } from '@/components/ui/switch';
import type { LayerKey } from '@/lib/campus/types';

const LAYER_ITEMS: [LayerKey, string, typeof Building2][] = [
  ['labels', '地点名称', RectangleEllipsis],
  ['boundary', '校园边界', Scan],
  ['buildings', '校园建筑', Building2],
  ['vegetation', '树木', Trees],
  ['roads', '道路与桥梁', Navigation],
  ['water', '水面', Waves],
  ['sports', '运动场地', Dumbbell],
  ['context', '周边建筑', Layers3],
];

export function CampusLayerSettings({
  layers,
  onToggle,
}: {
  layers: Record<LayerKey, boolean>;
  onToggle: (key: LayerKey, on: boolean) => void;
}) {
  const { t } = useCampusLocale();
  return LAYER_ITEMS.map(([key, label, Icon]) => (
    <label className="layer-row" key={key} htmlFor={`layer-${key}`}>
      <Icon size={19} />
      <span id={`layer-title-${key}`}>{t(label)}</span>
      <Switch
        id={`layer-${key}`}
        checked={layers[key]}
        onCheckedChange={(on) => onToggle(key, on)}
        aria-labelledby={`layer-title-${key}`}
      />
    </label>
  ));
}
