import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { AccessService } from 'auth';
import { SideNavigationService, ToolbarService } from 'navigation';
import { of } from 'rxjs';

@Component({
  selector: 'lib-community-dashboard',
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
    private toolbarService: ToolbarService,
    private sideNavigationService: SideNavigationService,
    private accessService: AccessService,
    private activatedRoute: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    const site = this.activatedRoute.snapshot.params['name']
    this.toolbarService.title.next({
      top: null,
      bottom: 'Community Dashboard',
      routerLinkTop: `/sites/${site}/CommunityDashboard`,
      routerLinkBottom: `/sites/${site}/CommunityDashboard`,
    })
    this.sideNavigationService.logo.next({
      light: '/assets/ohdsi-logo-with-text-199-light.png',
      dark: '/assets/ohdsi-logo-with-text-199-dark.png'
    })
    this.toolbarService.hideSideNav.next(false)
    this.sideNavigationService.routes.next([
      {
        link: `/sites/${site}/Community Dashboard/pubmed`,
        disabled: of(false),
        name: 'Publications',
      },
      {
        link: `/sites/${site}/Community Dashboard/youtube`,
        disabled: of(false),
        name: 'YouTube'
      },
      {
        link: `/sites/${site}/Community Dashboard/ehden`,
        disabled: of(false),
        name: 'Ehden Courses'
      },
      {
        link: `/sites/${site}/Community Dashboard/study-explorer`,
        disabled: of(false),
        name: 'Network Studies'
      },
    ])
  }

  accessSubscription = this.accessService.active.subscribe(
    a => {
      if (a) {
        this.toolbarService.hideSites.next(false)
        this.toolbarService.hideUser.next(false)
        this.sideNavigationService.hidePackages.next(false)
        this.sideNavigationService.hideSettings.next(false)
      } else {
        this.toolbarService.hideSites.next(true)
        this.toolbarService.hideUser.next(true)
        this.sideNavigationService.hidePackages.next(true)
        this.sideNavigationService.hideSettings.next(true)
      }
    }
  )

  ngOnDestroy(): void {
    this.toolbarService.reset()
    this.sideNavigationService.reset()
    this.accessSubscription.unsubscribe()
  }

}
