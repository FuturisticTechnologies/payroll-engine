import { Routes } from '@angular/router';

export const appRoutes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'employees',
    loadComponent: () =>
      import('./features/employees/employees.component').then((m) => m.EmployeesComponent),
  },
  {
    path: 'health',
    loadComponent: () =>
      import('./features/health/health.component').then((m) => m.HealthComponent),
  },
  { path: '**', redirectTo: '' },
];
