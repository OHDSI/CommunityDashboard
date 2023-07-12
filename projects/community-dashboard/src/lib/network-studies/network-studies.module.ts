import { NgModule } from '@angular/core';
import { Routes } from '@angular/router';
import { RouterModule } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./network-studies.component').then(mod => mod.NetworkStudiesComponent)
  },
  {
    path: 'repo/:repoId',
    loadComponent: () => import('./repo-drilldown/repo-drilldown.component').then(mod => mod.RepoDrilldownComponent)
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
export class NetworkStudiesModule { }
