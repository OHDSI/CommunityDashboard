import { provideHttpClient } from '@angular/common/http';
import { enableProdMode, ErrorHandler } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter, Route } from '@angular/router';
import { environment } from './app/environments/environment';
// import { RestMock } from './test/rest-mock.service';
// import { RestToken } from 'rest';
import { AppComponent } from './app/app.component';
import { RestMock } from './test/rest-mock.service';
import { RestToken } from 'rest';
// import { TestComponent } from './app/test.component';
// import { CommunityDashboardModule } from 'community-dashboard';


if (environment.production) {
  enableProdMode();
}

const ROUTES: Route[] = [
  {
    path: '',
    loadComponent: () => import('./app/navigation/navigation.component').then(mod => mod.NavigationComponent),
    loadChildren: () => import('community-dashboard').then(mod => mod.CommunityDashboardModule),
  },
  // {
  //   path: '**',
  //   loadChildren: () => import('community-dashboard').then(mod => mod.CommunityDashboardModule),
  //   // loadComponent: () => import('./app/community-dashboard.component').then(mod => mod.CommunityDashboardComponent),
  //   loadChildren: () => import('community-dashboard').then(mod => mod.CommunityDashboardModule),
  //   // loadComponent: () => NavigationComponent,
  //   // loadChildren: () => import('test').then(mod => mod.TestModule)
  //   // children: [
  //   //   {
  //   //     path: 'test',
  //   //     component: TestComponent
  //   //   }
  //   // ]
  // },
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
    {provide: RestToken, useClass: RestMock},
  ]
})
