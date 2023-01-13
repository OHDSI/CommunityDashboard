import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { PubMedComponent } from './pub-med.component';

describe('PubMedComponent', () => {
  let component: PubMedComponent;
  let fixture: ComponentFixture<PubMedComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        PubMedComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PubMedComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
