import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { EhdenComponent } from './ehden.component';

describe('EhdenComponent', () => {
  let component: EhdenComponent;
  let fixture: ComponentFixture<EhdenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ 
        EhdenComponent,
        HttpClientTestingModule,
        NoopAnimationsModule,
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EhdenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
