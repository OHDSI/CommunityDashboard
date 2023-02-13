import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatListModule } from '@angular/material/list';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-navigation',
  standalone: true,
  imports: [
    MatSidenavModule,
    MatListModule,
    RouterModule,
    CommonModule
  ],
  templateUrl: './navigation.component.html',
  styleUrls: ['./navigation.component.css']
})
export class NavigationComponent {

  links = [
    {routerLink: '/'},
    {routerLink: '/pubmed'},
    {routerLink: '/youtube'},
    {routerLink: '/ehden'},
    {routerLink: '/study-explorer'},
    {routerLink: '/funding'},
  ]

}
