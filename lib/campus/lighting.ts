import type { Preset } from './types';

/** Artistic daylight studies, not a solar-position or measured illuminance model. */
export const LIGHTING: Record<
  Preset,
  {
    sun: string;
    power: number;
    hemisphere: number;
    skyLight: string;
    bounce: string;
    fill: string;
    fillPower: number;
    environment: number;
    exposure: number;
    direction: [number, number, number];
  }
> = {
  morning: {
    sun: '#e9f2ff',
    power: 3.0,
    hemisphere: 0.78,
    skyLight: '#ccdef5',
    bounce: '#79836c',
    fill: '#b6d0ed',
    fillPower: 0.2,
    environment: 0.25,
    exposure: 1.0,
    direction: [-1300, 620, 700],
  },
  day: {
    sun: '#fff3de',
    power: 3.35,
    hemisphere: 0.72,
    skyLight: '#d4e6fa',
    bounce: '#818363',
    fill: '#c3dcec',
    fillPower: 0.18,
    environment: 0.24,
    exposure: 1.0,
    direction: [-700, 1400, 600],
  },
  evening: {
    sun: '#ffd0a0',
    power: 3.65,
    hemisphere: 0.6,
    skyLight: '#d9ddec',
    bounce: '#85715f',
    fill: '#b5c7e3',
    fillPower: 0.12,
    environment: 0.19,
    exposure: 0.98,
    direction: [1450, 270, 650],
  },
  night: {
    sun: '#aac8ed',
    power: 0.32,
    hemisphere: 0.12,
    skyLight: '#7895bc',
    bounce: '#253342',
    fill: '#779ec8',
    fillPower: 0.04,
    environment: 0.055,
    exposure: 0.86,
    direction: [-700, 1000, -600],
  },
};
