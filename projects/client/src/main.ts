import { provideHttpClient } from '@angular/common/http';
import { enableProdMode, ErrorHandler } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Route } from '@angular/router';
import { AppComponent } from './app/app.component';

import { environment } from './environments/environment';

if (environment.production) {
  enableProdMode();
}

const ROUTES: Route[] = [
  { path: '', loadComponent: () => import('./app/dashboard/dashboard.component').then(mod => mod.DashboardComponent) },
  { path: 'pubmed', loadComponent: () => import('./app/pub-med/pub-med.component').then(mod => mod.PubMedComponent) },
  { path: 'youtube', loadComponent: () => import('./app/you-tube/you-tube.component').then(mod => mod.YouTubeComponent) },
  { path: 'ehden', loadComponent: () => import('./app/ehden/ehden.component').then(mod => mod.EhdenComponent) },
  { path: '**',   redirectTo: '', pathMatch: 'full' },
];

class AppErrorHandler implements ErrorHandler {
  handleError(error: any) {
    console.error(error)
  }
}

bootstrapApplication(AppComponent, {
  providers: [
    {provide: ErrorHandler, useClass: AppErrorHandler},
    provideRouter(ROUTES),
    provideAnimations(),
    provideHttpClient(),
  ]
})
