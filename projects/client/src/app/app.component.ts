import { Component, ViewChild } from '@angular/core';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Observable } from 'rxjs';
import { map, shareReplay, tap } from 'rxjs/operators';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { CommonModule, LocationStrategy, PathLocationStrategy } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import {MatListModule} from '@angular/material/list';
import { RouterModule, RouterOutlet } from '@angular/router';


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    RouterOutlet,
    MatSidenavModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  providers: [Location, {provide: LocationStrategy, useClass: PathLocationStrategy}]
})
export class AppComponent {

  location
  drawerToggles!: boolean

  upToLarge: Observable<boolean> = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium])
  .pipe(
    map(result => result.matches),
    tap(upToLarge => this.drawerToggles = upToLarge)
  );

  toolbarHeight: Observable<number> = this.breakpointObserver.observe([Breakpoints.XSmall])
  .pipe(
    map(result => result.matches ? 56 : 64)
  );

  prefersColorScheme: string = 'dark'

  constructor(
    private breakpointObserver: BreakpointObserver,
  ) {
    this.location = location
    const updatePrefersColorScheme = () => {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updatePrefersColorScheme)
      this.prefersColorScheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    updatePrefersColorScheme()
  }

  px(px: number) {
    return `${px}px`
  }

}
