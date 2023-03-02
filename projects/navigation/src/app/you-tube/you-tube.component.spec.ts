import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';


import { YouTubeComponent } from './you-tube.component';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('YouTubeComponent', () => {
  let component: YouTubeComponent;
  let fixture: ComponentFixture<YouTubeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        YouTubeComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(YouTubeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
