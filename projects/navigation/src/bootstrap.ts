import { provideHttpClient } from '@angular/common/http';
import { enableProdMode, ErrorHandler } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Route } from '@angular/router';
import { environment } from './app/environments/environment';
import { AppComponent } from './app/app.component';
import { RestMock } from './test/rest-mock.service';
import { DocsMock } from './test/docs-mock.service';
import { AuthMockService } from './test/auth-mock.service';

if (environment.production) {
  enableProdMode();
}

const ROUTES: Route[] = [
  {
    path: '',
    loadComponent: () => import('./app/navigation/navigation.component').then(mod => mod.NavigationComponent),
    loadChildren: () => import('./app/community-dashboard.module').then(mod => mod.CommunityDashboardModule),
  },
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
    {provide: 'environment', useValue: environment},
    // {provide: RestToken, useClass: RestMock},
    {provide: 'RestToken', useClass: RestMock},
    {provide: 'DocsToken', useClass: DocsMock},
    {provide: 'AuthToken', useClass: AuthMockService},
  ]
})
