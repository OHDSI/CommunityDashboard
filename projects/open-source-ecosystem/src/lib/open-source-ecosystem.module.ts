import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./open-source-ecosystem.component').then(mod => mod.OpenSourceEcosystemComponent)
  },
  {
    path: 'project/:projectId',
    loadComponent: () => import('./project-drilldown/project-drilldown.component').then(mod => mod.ProjectDrilldownComponent)
  }
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
export class OpenSourceEcosystemModule { }
