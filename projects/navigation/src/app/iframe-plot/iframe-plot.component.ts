import { ChangeDetectorRef, Component, ElementRef, Inject, inject, Input, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SafeUrlPipe } from './safe-url.pipe';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { IframeTokenBucketService } from './iframe-token-bucket.service';

@Component({
  selector: 'app-iframe-plot',
  standalone: true,
  imports: [
    MatProgressSpinnerModule,
    MatButtonModule,
    SafeUrlPipe,
    CommonModule
  ],
  templateUrl: './iframe-plot.component.html',
  styleUrls: ['./iframe-plot.component.css']
})
export class IframePlotComponent implements OnDestroy {

  @Input() path!: string

  @ViewChild('plotContainer', { read: ElementRef }) plotContainer!: ElementRef

  plotSrc: string | null = null
  plotSubscription?: number
  dashDelay = false
  retryDelay = false

  constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private iframeTokenBucketService: IframeTokenBucketService,
    @Inject('environment') private environment: any,
  ) {}

  ngOnDestroy(): void {
    if (this.plotSubscription) {
      this.iframeTokenBucketService.unsubscribePlotDequeue(this.plotSubscription)
    }
  }

  ngAfterViewInit(): void {
    setTimeout(() => { this.dashDelay = true}, 2000)
    setTimeout(() => { this.retryDelay = true}, 10000)
    this.plotSubscription = this.iframeTokenBucketService.subscribePlotDequeue(() => this.plot())
    new ResizeObserver(() => {
      this.iframeTokenBucketService.queueResize()
    }).observe(this.plotContainer.nativeElement)   
  }

  _height = 0
  _width = 0
  plot(): void {
    const height = this.plotContainer.nativeElement.offsetHeight
    if (!height) {
      // Mid-render, requeue.
      new ResizeObserver(() => this.plot()).observe(this.plotContainer.nativeElement)  
      return
    }
    const width = this.plotContainer.nativeElement.offsetWidth
    if (height != this._height || width != this._width) {
      this._height = height
      this._width = width
      this.plotSrc = `${this.environment.plots}/${this.path}?height=${height}px&width=${width}`
      this.changeDetectorRef.detectChanges()
    }
  }
}
