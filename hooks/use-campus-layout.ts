import { useEffect, useRef, useState, type RefObject } from 'react';
import type { SceneController } from '@/lib/campus/types';

/**
 * Mirrors the visual viewport into CSS variables on the app root and reports
 * whether a narrow layout is covered by the on-screen keyboard.
 */
export function useVisualViewport(host: RefObject<HTMLElement | null>) {
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  useEffect(() => {
    const viewport = window.visualViewport;
    const update = () => {
      const root = host.current?.parentElement;
      const height = viewport?.height ?? window.innerHeight;
      root?.style.setProperty('--app-height', `${height}px`);
      root?.style.setProperty(
        '--viewport-top',
        `${viewport?.offsetTop ?? 0}px`,
      );
      setKeyboardOpen(
        window.innerWidth < 760 && height < window.innerHeight * 0.75,
      );
    };
    update();
    viewport?.addEventListener('resize', update);
    viewport?.addEventListener('scroll', update);
    window.addEventListener('resize', update);
    return () => {
      viewport?.removeEventListener('resize', update);
      viewport?.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, [host]);
  return keyboardOpen;
}

/**
 * Measures the map area left visible by the header, panel and tools, and
 * passes it to the scene. Each new `framingRequest` recomposes the camera even
 * when the area is unchanged.
 */
export function useSceneFrame({
  ready,
  collapsed,
  framingRequest,
  host,
  dock,
  controller,
}: {
  ready: boolean;
  collapsed: boolean;
  framingRequest: number;
  host: RefObject<HTMLElement | null>;
  dock: RefObject<HTMLElement | null>;
  controller: RefObject<SceneController | null>;
}) {
  const framedRequest = useRef(0);
  useEffect(() => {
    if (!ready || !host.current || !dock.current) return;
    const root = host.current.parentElement!;
    const header = root.querySelector<HTMLElement>('.masthead')!;
    const tools = root.querySelector<HTMLElement>('.map-tools')!;
    let pending = 0;
    let previous = '';
    const measure = () => {
      cancelAnimationFrame(pending);
      pending = requestAnimationFrame(() => {
        const panel = dock.current!.getBoundingClientRect();
        const menu = tools.getBoundingClientRect();
        const top = header.getBoundingClientRect().bottom + 18;
        const mobile = window.innerWidth < 760;
        const left = mobile || collapsed ? 18 : panel.right + 24;
        const right = menu.left - 18;
        const bottom = mobile ? panel.top - 34 : window.innerHeight - 42;
        const frame = {
          left,
          top,
          width: Math.max(120, right - left),
          height: Math.max(100, bottom - top),
        };
        root.style.setProperty('--dock-height', `${panel.height}px`);
        root.style.setProperty('--scene-left', `${left}px`);
        const key = JSON.stringify(frame);
        const reframe = framedRequest.current !== framingRequest;
        if (key !== previous || reframe) {
          previous = key;
          framedRequest.current = framingRequest;
          controller.current?.setViewport(frame, reframe);
        }
      });
    };
    const observer = new ResizeObserver(measure);
    [dock.current, header, tools, host.current].forEach((el) =>
      observer.observe(el),
    );
    measure();
    return () => {
      observer.disconnect();
      cancelAnimationFrame(pending);
    };
  }, [ready, collapsed, framingRequest, host, dock, controller]);
}
