import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

export const appRoutes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./features/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: '',
    pathMatch: 'full',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'employees',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/employees/employees.component').then((m) => m.EmployeesComponent),
  },
  {
    path: 'framework',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/framework/framework.component').then((m) => m.FrameworkComponent),
  },
  {
    path: 'health',
    loadComponent: () =>
      import('./features/health/health.component').then((m) => m.HealthComponent),
  },
  { path: '**', redirectTo: '' },
];
