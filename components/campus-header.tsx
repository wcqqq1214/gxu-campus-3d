import { Menu } from '@base-ui/react/menu';
import { Check, Globe } from 'lucide-react';
import { useCampusLocale } from '@/components/campus-locale';
import { asset } from '@/lib/campus/boot';

export function CampusHeader({ onHome }: { onHome: () => void }) {
  const { locale, setLocale, t } = useCampusLocale();
  return (
    <header className="masthead">
      <div className="masthead-brand">
        <button
          className="brand-mark"
          onClick={onHome}
          title={t('回到全景')}
          aria-label={t('回到全景')}
        >
          <img src={asset('favicon.svg')} alt="" width={44} height={44} />
        </button>
        <h1>
          {t('广西大学')}
          <span>{t('校园地图')}</span>
        </h1>
      </div>
      <div className="masthead-actions">
        <Menu.Root>
          <Menu.Trigger className="header-action" aria-label="语言 / Language">
            <Globe size={18} aria-hidden="true" />
          </Menu.Trigger>
          <Menu.Portal>
            <Menu.Positioner
              className="language-menu-positioner"
              side="bottom"
              align="end"
              sideOffset={8}
            >
              <Menu.Popup
                className="language-menu"
                aria-label="语言 / Language"
              >
                <Menu.RadioGroup value={locale} onValueChange={setLocale}>
                  <Menu.RadioItem
                    className="language-menu-item"
                    value="zh"
                    closeOnClick
                  >
                    <span lang="zh-CN">中文</span>
                    <Menu.RadioItemIndicator>
                      <Check size={16} aria-hidden="true" />
                    </Menu.RadioItemIndicator>
                  </Menu.RadioItem>
                  <Menu.RadioItem
                    className="language-menu-item"
                    value="en"
                    closeOnClick
                  >
                    <span lang="en">English</span>
                    <Menu.RadioItemIndicator>
                      <Check size={16} aria-hidden="true" />
                    </Menu.RadioItemIndicator>
                  </Menu.RadioItem>
                </Menu.RadioGroup>
              </Menu.Popup>
            </Menu.Positioner>
          </Menu.Portal>
        </Menu.Root>
        <a
          className="header-action"
          href="https://github.com/wcqqq1214/gxu-campus-3d"
          target="_blank"
          rel="noreferrer"
          aria-label={t('查看 GitHub 仓库')}
        >
          <svg
            width={18}
            height={18}
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
            focusable="false"
          >
            <path d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.043-1.61-4.043-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.084 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.418-1.305.762-1.605-2.665-.3-5.466-1.334-5.466-5.93 0-1.31.467-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 0 1 3-.404c1.02.005 2.045.138 3 .404 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
          </svg>
        </a>
      </div>
    </header>
  );
}
