import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'lib-community-dashboard',
  standalone: true,
  imports: [
    RouterModule,
    CommonModule
  ],
  templateUrl: './community-dashboard.component.html',
  styleUrls: ['./community-dashboard.component.css']
})
export class CommunityDashboardComponent {

}
