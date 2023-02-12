import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-community-dashboard',
  standalone: true,
  imports: [
    RouterModule,
    CommonModule
  ],
  template: `
    <router-outlet></router-outlet>
  `,
  styles: [
  ]
})
export class CommunityDashboardComponent {

  constructor(
  ) {}

}
