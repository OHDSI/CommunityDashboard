import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [

  { path: '', pathMatch: "full", loadComponent: () => import('./dashboard/dashboard.component').then(mod => mod.DashboardComponent) },
  { path: 'pubmed', loadComponent: () => import('./pub-med/pub-med.component').then(mod => mod.PubMedComponent) },
  { path: 'youtube', loadComponent: () => import('./you-tube/you-tube.component').then(mod => mod.YouTubeComponent) },
  { path: 'ehden', loadComponent: () => import('./ehden/ehden.component').then(mod => mod.EhdenComponent) },
  { path: 'study-explorer', loadComponent: () => import('./study-explorer/study-explorer.component').then(mod => mod.StudyExplorerComponent) },
  { path: 'funding', loadComponent: () => import('./funding/funding.component').then(mod => mod.FundingComponent) },
]

@NgModule({
  declarations: [
  ],
  imports: [
    RouterModule.forChild(routes)
  ],
  exports: [
  ]
})
export class CommunityDashboardModule { }
