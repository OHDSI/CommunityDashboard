import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IframePlotComponent } from './iframe-plot.component';

describe('IframePlotComponent', () => {
  let component: IframePlotComponent;
  let fixture: ComponentFixture<IframePlotComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ IframePlotComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(IframePlotComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
