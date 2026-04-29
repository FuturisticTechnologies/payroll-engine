import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'pf-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="pf-shell">
      <aside class="pf-sidebar">
        <div class="pf-brand">
          <span class="pf-brand__mark">PF</span>
          <div class="pf-brand__text">
            <strong>PayrollFuturistic</strong>
            <small>Snovasys · UK HMRC-ready</small>
          </div>
        </div>

        <nav class="pf-nav">
          <a routerLink="/" routerLinkActive="pf-nav__item--active" [routerLinkActiveOptions]="{ exact: true }" class="pf-nav__item">
            Dashboard
          </a>
          <a routerLink="/employees" routerLinkActive="pf-nav__item--active" class="pf-nav__item">
            Employees
          </a>
          <a routerLink="/health" routerLinkActive="pf-nav__item--active" class="pf-nav__item">
            System health
          </a>
        </nav>

        <footer class="pf-sidebar__footer">
          <small>Milestone 1 · Apr&nbsp;2026</small>
        </footer>
      </aside>

      <main class="pf-main">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
        height: 100%;
      }

      .pf-shell {
        display: grid;
        grid-template-columns: 260px 1fr;
        min-height: 100vh;
      }

      .pf-sidebar {
        background: var(--pf-color-primary);
        color: #fff;
        padding: 24px 20px;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .pf-brand {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .pf-brand__mark {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        background: var(--pf-color-accent);
        color: #072a43;
        display: grid;
        place-items: center;
        font-weight: 800;
      }

      .pf-brand__text strong {
        display: block;
        font-size: 15px;
      }

      .pf-brand__text small {
        opacity: 0.75;
        font-size: 11px;
      }

      .pf-nav {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .pf-nav__item {
        color: #dbeafe;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 14px;
      }

      .pf-nav__item:hover {
        background: rgba(255, 255, 255, 0.06);
        text-decoration: none;
      }

      .pf-nav__item--active {
        background: rgba(255, 255, 255, 0.12);
        color: #fff;
      }

      .pf-sidebar__footer {
        margin-top: auto;
        opacity: 0.6;
      }

      .pf-main {
        padding: 32px 40px;
        overflow-y: auto;
      }
    `,
  ],
})
export class AppComponent {}
