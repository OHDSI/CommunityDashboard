import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { Routes } from '@angular/router';

const routes: Routes = [
    {
      path: '',
      loadComponent: () => import('./landing/landing.component').then(mod => mod.LandingComponent)
    },
    {
      path: 'open-source-ecosystem',
      loadChildren: () => import('./open-source-ecosystem/open-source-ecosystem.module').then(mod => mod.OpenSourceEcosystemModule)
    },
    {
      path: 'network-studies',
      loadChildren: () => import('./network-studies/network-studies.module').then(mod => mod.NetworkStudiesModule)
    },
  ];

@NgModule({
  declarations: [
  ],
  imports: [
    RouterModule.forChild(routes),
  ],
  exports: [
  ]
})
export class CommunityDashboardModule { }
