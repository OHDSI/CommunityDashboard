import { Component, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { IframePlotComponent } from '../iframe-plot/iframe-plot.component';
import { Subscription } from 'rxjs';
import { EhdenService } from '../ehden/ehden.service';
import { renderPlot } from '../ehden/ehden-users-annually-plot';


@Component({
  selector: 'app-ehden-tabs',
  standalone: true,
  imports: [
    IframePlotComponent,
    MatTabsModule,
    CommonModule
  ],
  templateUrl: './ehden-tabs.component.html',
  styleUrls: ['./ehden-tabs.component.css']
})
export class EhdenTabsComponent {
  @ViewChild('ehdenUsersAnnuallyPlot', {read: ElementRef}) ehdenUsersAnnuallyPlot!: ElementRef

  constructor(
    private ehdenService: EhdenService
  ){}

  ngAfterViewInit(): void {
    this.ehdenServiceSubscription = this.ehdenService.valueChanges().subscribe(es => {
      if (!es) {
        this.ehdenUsersAnnuallyPlot.nativeElement.replaceChildren(null)
        return
      }
      this.ehdenUsersAnnuallyPlot.nativeElement.replaceChildren(renderPlot(es[0]))
  })
  }

  ehdenServiceSubscription?: Subscription

  ngOnDestroy(): void {
    this.ehdenServiceSubscription?.unsubscribe()
  }
}
